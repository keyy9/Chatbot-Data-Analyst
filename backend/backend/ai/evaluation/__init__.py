"""Model evaluation module."""

from backend.ai.evaluation.evaluator import (
    ModelEvaluator,
    EvaluationResult,
    EvaluationMetric,
    SQLCorrectnessTester,
    AnswerQualityEvaluator,
    HallucinationDetector,
    SchemaComplianceChecker,
    get_model_evaluator
)

__all__ = [
    "ModelEvaluator",
    "EvaluationResult",
    "EvaluationMetric",
    "SQLCorrectnessTester",
    "AnswerQualityEvaluator",
    "HallucinationDetector",
    "SchemaComplianceChecker",
    "get_model_evaluator",
]