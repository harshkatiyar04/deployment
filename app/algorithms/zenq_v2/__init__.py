"""ZenQ v2 cumulative impact algorithm (Board Standalone v2.1 + Tech Guide).

Product scoring engine ships under LAUNCH_PARAMS = full design dials
(g_slope 0.6, agent.apply, all chat/KIA/CSR flags). CONSERVATIVE_LAUNCH_PARAMS
preserves pre-cutover gates for rollback tests. Archive 1.5.1 board unchanged.
"""

from app.algorithms.zenq_v2.params import (
    ALGORITHM_VERSION,
    CONSERVATIVE_LAUNCH_PARAMS,
    DESIGN_PARAMS,
    LAUNCH_PARAMS,
)
from app.algorithms.zenq_v2.scoring import score_event, streak_mult, session_ip

__all__ = [
    "ALGORITHM_VERSION",
    "LAUNCH_PARAMS",
    "DESIGN_PARAMS",
    "CONSERVATIVE_LAUNCH_PARAMS",
    "score_event",
    "streak_mult",
    "session_ip",
]
