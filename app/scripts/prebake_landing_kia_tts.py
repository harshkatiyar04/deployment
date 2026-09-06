"""Pre-warm Edge audio for common Kia answers (fast path).

From zenkimpact_BE:
  python -m app.scripts.prebake_landing_kia_tts
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.landing_kia_rag import _FAST, _apply_opener, _normalize_q  # noqa: E402
from app.services.landing_kia_tts import synthesize  # noqa: E402


async def main() -> None:
    texts = [_apply_opener(body, salt=_normalize_q(q)) for q, body in _FAST.items()]
    uniq = list(dict.fromkeys(t.strip() for t in texts if t.strip()))
    print(f"prebaking {len(uniq)} common answers...")
    ok = 0
    for i, text in enumerate(uniq, 1):
        result = await synthesize(text, allow_slow=False)
        if result:
            ok += 1
        print(f"  [{i}/{len(uniq)}] {'ok' if result else 'fail'}  {text[:72]}...")
    print(f"done: {ok}/{len(uniq)} — repeats will be instant")


if __name__ == "__main__":
    asyncio.run(main())
