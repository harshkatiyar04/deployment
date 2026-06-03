from __future__ import annotations

BASE_IMPACT = 100.0
DECAY_RATE = 0.04
SPARK_MULTIPLIER = 1.5

DEFAULT_WEIGHTS = {
    "T": 0.25,
    "A": 0.30,
    "S": 0.25,
    "Cm": 0.10,
    "In": 0.05,
    "E": 0.03,
    "C": 0.02,
}

WEIGHT_BOUNDS = {
    "T": (0.10, 0.40),
    "A": (0.15, 0.45),
    "S": (0.10, 0.40),
    "Cm": (0.03, 0.20),
    "In": (0.03, 0.15),
    "E": (0.03, 0.10),
    "C": (0.03, 0.10),
}

MAX_SHIFT_PER_CYCLE = 0.05

# School ZQA v2 (holistic composite)
ZQA_PILLAR_WEIGHTS = {
    "academic": 0.50,
    "blooms": 0.25,
    "sel": 0.25,
}

ZQA_ACADEMIC_WEIGHTS = {
    "english": 0.30,
    "maths": 0.28,
    "science": 0.22,
    "history": 0.20,
}

ZQA_ACADEMIC_KEYS = ("english", "maths", "science", "history")

ZQA_BLOOMS_LEVEL_WEIGHTS = {
    "remember": 0.05,
    "understand": 0.10,
    "apply": 0.20,
    "analyse": 0.25,
    "evaluate": 0.25,
    "create": 0.15,
}

ZQA_SEL_KEYS = (
    "self_awareness",
    "self_management",
    "social_awareness",
    "relationship_skills",
    "responsible_decisions",
)

ZQA_MIN_ACADEMIC_SUBJECTS = 2
ZQA_MAX_SINGLE_SUBJECT_CAP = 60.0
ZQA_ATTENDANCE_FLOOR_PCT = 92.0
