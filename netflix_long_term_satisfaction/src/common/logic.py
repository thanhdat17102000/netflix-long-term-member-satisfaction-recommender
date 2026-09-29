from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.common.config import MOVIELENS_HEADERS


@dataclass(frozen=True)
class UserHistory:
    user_id: int
    rating_count: int
    first_timestamp: int
    last_timestamp: int

    @property
    def activity_span_days(self) -> float:
        return (self.last_timestamp - self.first_timestamp) / 86400.0


def is_long_term(history: UserHistory, min_days: float = 180, min_ratings: int = 20) -> bool:
    return history.rating_count >= min_ratings and history.activity_span_days >= min_days


def is_positive_rating(rating: float, threshold: float = 4.0) -> bool:
    return rating >= threshold


def is_valid_rating_value(rating: float, low: float = 0.5, high: float = 5.0) -> bool:
    return low <= float(rating) <= high


def header_fields(header: str) -> list[str]:
    return [part.strip() for part in header.strip().split(",") if part.strip() or part == ""]


def schema_is_valid(filename: str, header: str) -> bool:
    expected = MOVIELENS_HEADERS.get(filename)
    if expected is None:
        return False
    return header_fields(header) == expected


def temporal_split_bounds(
    count: int,
    train_ratio: float = 0.8,
    validation_ratio: float = 0.1,
) -> tuple[int, int]:
    """Return train and validation end positions, keeping all three splits nonempty."""
    if count < 3:
        raise ValueError("Cần ít nhất ba lượt chấm để chia dữ liệu thành train, validation và test")
    train_end = max(1, min(int(count * train_ratio), count - 2))
    validation_end = max(train_end + 1, min(int(count * (train_ratio + validation_ratio)), count - 1))
    return train_end, validation_end


def temporal_split_indices(
    timestamps: Iterable[int],
    train_ratio: float = 0.8,
    validation_ratio: float = 0.1,
) -> tuple[list[int], list[int], list[int]]:
    values = sorted(timestamps)
    train_end, validation_end = temporal_split_bounds(len(values), train_ratio, validation_ratio)
    return values[:train_end], values[train_end:validation_end], values[validation_end:]


def temporal_order_is_valid(
    train_timestamps: Iterable[int],
    validation_timestamps: Iterable[int],
    test_timestamps: Iterable[int],
) -> bool:
    train = list(train_timestamps)
    validation = list(validation_timestamps)
    test = list(test_timestamps)
    if not train or not validation or not test:
        return False
    return max(train) < min(validation) and max(validation) < min(test)


def exclude_train_items(candidates: Iterable[int], train_items: Iterable[int]) -> list[int]:
    seen = set(train_items)
    return [item for item in candidates if item not in seen]


def recommendations_are_unique(items: Iterable[int]) -> bool:
    values = list(items)
    return len(values) == len(set(values))


def has_null_or_duplicate(rows: list[tuple], key_indexes: Iterable[int] | None = None) -> bool:
    if any(any(value is None or value == "" for value in row) for row in rows):
        return True
    keys = []
    indexes = list(key_indexes) if key_indexes is not None else list(range(len(rows[0]))) if rows else []
    for row in rows:
        keys.append(tuple(row[index] for index in indexes))
    return len(keys) != len(set(keys))
