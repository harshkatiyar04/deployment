"""Landing Kia TTS — fast first, natural voice when cached.

Strategy:
  1. Serve disk cache instantly when present
  2. On miss: Sarvam (if key set) → Edge Neerja → Gemini last resort
  3. Optionally refresh Gemini in the background for next time
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
import os
import wave
from pathlib import Path

from app.core.settings import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / "storage" / "landing_kia_tts"
CACHE_VERSION = "sarvam-pooja-neerja-v1"

GEMINI_TTS_MODEL = os.getenv("LANDING_KIA_GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
GEMINI_VOICE = os.getenv("LANDING_KIA_GEMINI_VOICE", "Kore")
EDGE_VOICE = os.getenv("LANDING_KIA_EDGE_VOICE", "en-IN-NeerjaNeural")
# Match Sarvam female pace (~1.05) — mild +rate, not rushed
EDGE_RATE = os.getenv("LANDING_KIA_EDGE_RATE", "+5%")
GEMINI_BG = os.getenv("LANDING_KIA_GEMINI_BG", "0").strip() in ("1", "true", "True")

STYLE = (
    "Speak as Kia: a warm, friendly Indian woman guiding visitors on ZenK Impact. "
    "Natural conversational Indian English, calm and human — not robotic. Steady, clear pace."
)

_bg_tasks: set[asyncio.Task] = set()


def _cache_path(text: str, provider: str, ext: str) -> Path:
    digest = hashlib.sha256(f"{CACHE_VERSION}|{provider}|{text}".encode("utf-8")).hexdigest()[:40]
    return CACHE_DIR / f"{digest}.{ext}"


def _pcm16_to_wav(pcm: bytes, sample_rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setframerate(sample_rate)
        wf.setsampwidth(2)
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
    for provider, ext, mime in (
        ("gemini", "wav", "audio/wav"),
        ("gemini", "mp3", "audio/mpeg"),
        ("sarvam", "mp3", "audio/mpeg"),
        ("sarvam", "wav", "audio/wav"),
        ("edge", "mp3", "audio/mpeg"),
    ):
        path = _cache_path(cleaned, provider, ext)
        if path.exists() and path.stat().st_size > 0:
            return path.read_bytes(), mime
    return None


def _sarvam_enabled() -> bool:
    return bool((settings.sarvam_api_key or "").strip())


async def _sarvam_audio(text: str) -> tuple[bytes, str] | None:
    """Sarvam Bulbul TTS — warm Indian female voice when configured."""
    api_key = (settings.sarvam_api_key or "").strip()
    if not api_key:
        return None

    speaker = (settings.sarvam_speaker or "pooja").strip().lower()
    model = (settings.sarvam_model or "bulbul:v3").strip()
    lang = (settings.sarvam_language_code or "en-IN").strip()
    try:
        pace = float(settings.sarvam_pace or 1.05)
    except (TypeError, ValueError):
        pace = 1.05
    pace = max(0.5, min(2.0, pace))
    try:
        temperature = float(settings.sarvam_temperature or 0.55)
    except (TypeError, ValueError):
        temperature = 0.55
    temperature = max(0.01, min(2.0, temperature))

    cache_key = f"sarvam-{speaker}-p{pace:.2f}-t{temperature:.2f}"
    mp3_path = _cache_path(text, cache_key, "mp3")
    wav_path = _cache_path(text, cache_key, "wav")
    if mp3_path.exists() and mp3_path.stat().st_size > 0:
        return mp3_path.read_bytes(), "audio/mpeg"
    if wav_path.exists() and wav_path.stat().st_size > 0:
        return wav_path.read_bytes(), "audio/wav"

    try:
        import httpx
    except ImportError:
        logger.warning("httpx unavailable for Sarvam TTS")
        return None

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "language_code": lang,
        "model": model,
        "speaker": speaker,
        "pace": pace,
        "temperature": temperature,
        "speech_sample_rate": 24000,
        "output_audio_codec": "mp3",
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers=headers,
                json=body,
            )
        if resp.status_code != 200:
            logger.warning(
                "Sarvam TTS HTTP %s (speaker=%s): %s",
                resp.status_code,
                speaker,
                (resp.text or "")[:240],
            )
            return None
        payload = resp.json()
        audios = payload.get("audios") or []
        if not audios:
            logger.warning("Sarvam TTS empty audios for speaker=%s", speaker)
            return None
        audio = base64.b64decode(audios[0])
        if not audio:
            return None

        # Codec may still return wav depending on account/model; sniff magic
        if audio[:3] == b"ID3" or audio[:2] == b"\xff\xfb" or audio[:2] == b"\xff\xf3":
            mp3_path.write_bytes(audio)
            # Also alias generic provider cache for lookup_cached
            _cache_path(text, "sarvam", "mp3").write_bytes(audio)
            mime = "audio/mpeg"
        elif audio[:4] == b"RIFF":
            wav_path.write_bytes(audio)
            _cache_path(text, "sarvam", "wav").write_bytes(audio)
            mime = "audio/wav"
        else:
            mp3_path.write_bytes(audio)
            _cache_path(text, "sarvam", "mp3").write_bytes(audio)
            mime = "audio/mpeg"

        logger.info(
            "Kia Sarvam synth ok speaker=%s pace=%s (%s bytes)",
            speaker,
            pace,
            len(audio),
        )
        return audio, mime
    except Exception as exc:
        logger.warning("Sarvam TTS failed: %s", exc)
        for p in (mp3_path, wav_path):
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
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

    Default path is latency-first (cache → Sarvam if configured → Edge).
    Set allow_slow=True only for offline prebake scripts that intentionally wait on Gemini.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if len(cleaned) > 1200:
        cleaned = cleaned[:1200]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    hit = lookup_cached(cleaned)
    if hit:
        if GEMINI_BG and not _cache_path(cleaned, "gemini", "wav").exists():
            _schedule_gemini_upgrade(cleaned)
        return hit

    if allow_slow:
        gem = await asyncio.to_thread(_gemini_sync, cleaned)
        if gem:
            audio, mime = gem
            _save_gemini(cleaned, audio, mime)
            return audio, mime

    if _sarvam_enabled():
        sarvam = await _sarvam_audio(cleaned)
        if sarvam:
            return sarvam

    mp3 = await _edge_mp3(cleaned)
    if mp3:
        _schedule_gemini_upgrade(cleaned)
        return mp3, "audio/mpeg"

    gem = await asyncio.to_thread(_gemini_sync, cleaned)
    if gem:
        audio, mime = gem
        _save_gemini(cleaned, audio, mime)
        return audio, mime
    return None


async def synthesize_mp3(text: str) -> bytes | None:
    result = await synthesize(text)
    return result[0] if result else None
