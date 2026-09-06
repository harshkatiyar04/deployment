"""Landing Kia TTS — fast first, natural Gemini when cached.

Strategy:
  1. Serve Gemini/Edge disk cache instantly when present
  2. On miss: Edge Neerja immediately (~1–2s) so the UI stays snappy
  3. Optionally refresh Gemini in the background for next time (natural voice)

Live requests never wait on Gemini (that was the 10–15s delay).
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import wave
from pathlib import Path

from app.core.settings import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / "storage" / "landing_kia_tts"
CACHE_VERSION = "gemini31-kore-v2"

GEMINI_TTS_MODEL = os.getenv("LANDING_KIA_GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
GEMINI_VOICE = os.getenv("LANDING_KIA_GEMINI_VOICE", "Kore")
EDGE_VOICE = "en-IN-NeerjaNeural"
EDGE_RATE = "-4%"
# Background Gemini upgrade — OFF by default (free tier is ~10 TTS/day).
# Set LANDING_KIA_GEMINI_BG=1 only if you have paid quota.
GEMINI_BG = os.getenv("LANDING_KIA_GEMINI_BG", "0").strip() in ("1", "true", "True")

STYLE = (
    "Speak as Kia: a warm, friendly Indian woman guiding visitors on ZenK Impact. "
    "Natural conversational Indian English, calm and human — not robotic. Medium pace."
)

_bg_tasks: set[asyncio.Task] = set()


def _cache_path(text: str, provider: str, ext: str) -> Path:
    digest = hashlib.sha256(f"{CACHE_VERSION}|{provider}|{text}".encode("utf-8")).hexdigest()[:40]
    return CACHE_DIR / f"{digest}.{ext}"


def _pcm16_to_wav(pcm: bytes, sample_rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def lookup_cached(text: str) -> tuple[bytes, str] | None:
    """Instant disk lookup only (no network)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if len(cleaned) > 1200:
        cleaned = cleaned[:1200]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    gem = _cache_path(cleaned, "gemini", "wav")
    if gem.exists() and gem.stat().st_size > 0:
        return gem.read_bytes(), "audio/wav"
    gem_mp3 = _cache_path(cleaned, "gemini", "mp3")
    if gem_mp3.exists() and gem_mp3.stat().st_size > 0:
        return gem_mp3.read_bytes(), "audio/mpeg"
    edge = _cache_path(cleaned, "edge", "mp3")
    if edge.exists() and edge.stat().st_size > 0:
        return edge.read_bytes(), "audio/mpeg"
    return None


def _gemini_sync(text: str) -> tuple[bytes, str] | None:
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        logger.warning("google-genai unavailable: %s", exc)
        return None

    client = genai.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(
            model=GEMINI_TTS_MODEL,
            contents=f"{STYLE}\n\nSpeak this exactly (do not add extra words):\n{text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=GEMINI_VOICE)
                    )
                ),
            ),
        )
        part = resp.candidates[0].content.parts[0]
        raw = part.inline_data.data
        mime = (part.inline_data.mime_type or "").lower()
        if not raw:
            return None
        if "wav" in mime:
            return raw, "audio/wav"
        if "mpeg" in mime or "mp3" in mime:
            return raw, "audio/mpeg"
        return _pcm16_to_wav(raw, 24000), "audio/wav"
    except Exception as exc:
        logger.warning("Gemini TTS failed: %s", exc)
        return None


def _save_gemini(text: str, audio: bytes, mime: str) -> None:
    if mime == "audio/mpeg":
        _cache_path(text, "gemini", "mp3").write_bytes(audio)
    else:
        _cache_path(text, "gemini", "wav").write_bytes(audio)


async def _edge_mp3(text: str) -> bytes | None:
    try:
        import edge_tts
    except ImportError:
        return None
    path = _cache_path(text, "edge", "mp3")
    try:
        communicate = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
        await communicate.save(str(path))
        return path.read_bytes()
    except Exception as exc:
        logger.warning("edge-tts failed: %s", exc)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        return None


def _schedule_gemini_upgrade(text: str) -> None:
    if not GEMINI_BG:
        return
    if not (settings.gemini_api_key or "").strip():
        return
    gem = _cache_path(text, "gemini", "wav")
    if gem.exists() and gem.stat().st_size > 0:
        return

    async def _job() -> None:
        try:
            result = await asyncio.to_thread(_gemini_sync, text)
            if result:
                audio, mime = result
                _save_gemini(text, audio, mime)
                logger.info("Kia Gemini cache warmed (%s bytes)", len(audio))
        except Exception as exc:
            logger.debug("Gemini bg warm failed: %s", exc)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(_job())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


async def synthesize(text: str, *, allow_slow: bool = False) -> tuple[bytes, str] | None:
    """
    Return (audio_bytes, mime_type).

    Default path is latency-first (cache → Edge). Set allow_slow=True only for
    offline prebake scripts that intentionally wait on Gemini.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if len(cleaned) > 1200:
        cleaned = cleaned[:1200]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    hit = lookup_cached(cleaned)
    if hit:
        # Still top up Gemini in bg if we only have Edge
        if GEMINI_BG and not _cache_path(cleaned, "gemini", "wav").exists():
            _schedule_gemini_upgrade(cleaned)
        return hit

    if allow_slow:
        gem = await asyncio.to_thread(_gemini_sync, cleaned)
        if gem:
            audio, mime = gem
            _save_gemini(cleaned, audio, mime)
            return audio, mime

    mp3 = await _edge_mp3(cleaned)
    if mp3:
        _schedule_gemini_upgrade(cleaned)
        return mp3, "audio/mpeg"

    # Last resort: wait on Gemini if Edge unavailable
    gem = await asyncio.to_thread(_gemini_sync, cleaned)
    if gem:
        audio, mime = gem
        _save_gemini(cleaned, audio, mime)
        return audio, mime
    return None


async def synthesize_mp3(text: str) -> bytes | None:
    result = await synthesize(text)
    return result[0] if result else None
