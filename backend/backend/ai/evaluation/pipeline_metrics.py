"""
Pipeline Routing Metrics.

Computes a confusion matrix and per-class precision/recall/F1 for the
NL pipeline's routing decision - given a question, does it correctly end
up answered ("success"), asked for clarification ("clarification"), or
refused ("blocked")? Distinct from `evaluator.py`'s SQL-correctness
scoring: this measures whether the pipeline routes each question to the
right *outcome*, not whether a successfully-generated SQL statement is
the best possible one.

No external ML library dependency - the label set is small (3 classes)
and computing a confusion matrix / precision / recall / F1 from
(expected, actual) pairs is a few lines of arithmetic.
"""

from typing import Dict, List, Tuple


def compute_confusion_matrix(
    pairs: List[Tuple[str, str]],
    labels: List[str]
) -> Dict[str, Dict[str, int]]:
    """
    Build a confusion matrix from (expected, actual) label pairs.

    Args:
        pairs: List of (expected_label, actual_label) tuples.
        labels: The full ordered set of class labels.

    Returns:
        Dict: matrix[expected_label][actual_label] = count.
    """
    matrix = {expected: {actual: 0 for actual in labels} for expected in labels}
    for expected, actual in pairs:
        matrix[expected][actual] += 1
    return matrix


def compute_classification_metrics(
    pairs: List[Tuple[str, str]],
    labels: List[str]
) -> Dict:
    """
    Compute confusion matrix, per-class precision/recall/F1, macro
    averages, and overall accuracy from (expected, actual) label pairs.

    Args:
        pairs: List of (expected_label, actual_label) tuples.
        labels: The full ordered set of class labels.

    Returns:
        Dict: {
            "labels": [...],
            "confusion_matrix": {expected: {actual: count}},
            "per_class": {label: {"precision", "recall", "f1", "support"}},
            "macro_avg": {"precision", "recall", "f1"},
            "accuracy": float,
            "total": int
        }
    """
    matrix = compute_confusion_matrix(pairs, labels)
    total = len(pairs)

    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fn = sum(matrix[label][other] for other in labels if other != label)
        fp = sum(matrix[other][label] for other in labels if other != label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        support = tp + fn

        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support
        }

    macro_avg = {
        "precision": sum(c["precision"] for c in per_class.values()) / len(labels) if labels else 0.0,
        "recall": sum(c["recall"] for c in per_class.values()) / len(labels) if labels else 0.0,
        "f1": sum(c["f1"] for c in per_class.values()) / len(labels) if labels else 0.0
    }

    correct = sum(1 for expected, actual in pairs if expected == actual)
    accuracy = correct / total if total else 0.0

    return {
        "labels": labels,
        "confusion_matrix": matrix,
        "per_class": per_class,
        "macro_avg": macro_avg,
        "accuracy": accuracy,
        "total": total
    }
