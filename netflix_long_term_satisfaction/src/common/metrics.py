from __future__ import annotations

import math
from collections.abc import Iterable


def _relevant_set(relevant: Iterable[int]) -> set[int]:
    return set(relevant)


def precision_at_k(recommended: list[int], relevant: Iterable[int], k: int = 10) -> float:
    rel = _relevant_set(relevant)
    top = recommended[:k]
    return sum(item in rel for item in top) / max(len(top), 1)


def recall_at_k(recommended: list[int], relevant: Iterable[int], k: int = 10) -> float:
    rel = _relevant_set(relevant)
    return sum(item in rel for item in recommended[:k]) / max(len(rel), 1)


def ndcg_at_k(recommended: list[int], relevant: Iterable[int], k: int = 10) -> float:
    rel = _relevant_set(relevant)
    dcg = sum((1.0 / math.log2(index + 2)) for index, item in enumerate(recommended[:k]) if item in rel)
    ideal_hits = min(len(rel), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def hit_rate_at_k(recommended: list[int], relevant: Iterable[int], k: int = 10) -> float:
    return float(precision_at_k(recommended, relevant, k) > 0)


def map_at_k(recommended: list[int], relevant: Iterable[int], k: int = 10) -> float:
    rel = _relevant_set(relevant)
    score = 0.0
    hits = 0
    for index, item in enumerate(recommended[:k], start=1):
        if item in rel:
            hits += 1
            score += hits / index
    return score / max(min(len(rel), k), 1)


def satisfied_hit_rate_at_k(recommended: list[int], positive_items: Iterable[int], k: int = 10) -> float:
    return hit_rate_at_k(recommended, positive_items, k)


def catalog_coverage(recommended_items: Iterable[int], catalog_size: int) -> float:
    if catalog_size <= 0:
        return 0.0
    return len(set(recommended_items)) / catalog_size


def rmse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    pairs = [(float(actual), float(pred)) for actual, pred in zip(y_true, y_pred)]
    if not pairs:
        return float("nan")
    return math.sqrt(sum((actual - pred) ** 2 for actual, pred in pairs) / len(pairs))


def satisfaction_lift(model_rate: float, baseline_rate: float) -> float:
    if baseline_rate == 0:
        return 0.0
    return (model_rate - baseline_rate) / baseline_rate


def metric_in_unit_interval(value: float) -> bool:
    return 0.0 <= float(value) <= 1.0
