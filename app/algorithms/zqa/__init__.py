"""School ZQA (assessment composite) — live package; not ZenQ board 1.5.1."""

from app.algorithms.zqa.zqa import ZqaComputationResult, compute_zqa_result, validate_zqa_inputs

__all__ = [
    "ZqaComputationResult",
    "compute_zqa_result",
    "validate_zqa_inputs",
]
