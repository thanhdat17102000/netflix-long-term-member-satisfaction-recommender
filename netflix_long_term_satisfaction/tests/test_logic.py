from src.common.config import MOVIELENS_HEADERS
from src.common.logic import (
    UserHistory,
    exclude_train_items,
    has_null_or_duplicate,
    is_long_term,
    is_positive_rating,
    is_valid_rating_value,
    recommendations_are_unique,
    schema_is_valid,
    temporal_order_is_valid,
    temporal_split_bounds,
    temporal_split_indices,
)


def test_long_term_proxy():
    history = UserHistory(1, 20, 0, 180 * 86400)
    assert is_long_term(history)
    assert not is_long_term(UserHistory(2, 19, 0, 180 * 86400))
    assert not is_long_term(UserHistory(3, 20, 0, 179 * 86400))


def test_positive_rating():
    assert is_positive_rating(4.0)
    assert not is_positive_rating(3.5)


def test_rating_range():
    assert is_valid_rating_value(0.5)
    assert is_valid_rating_value(5.0)
    assert not is_valid_rating_value(0.0)
    assert not is_valid_rating_value(5.5)


def test_temporal_split_is_ordered():
    train, validation, test = temporal_split_indices(range(10))
    assert train and validation and test
    assert max(train) < min(validation) < min(test)


def test_temporal_split_keeps_three_parts_for_small_users():
    train, validation, test = temporal_split_indices([10, 20, 30, 40, 50])
    assert train and validation and test
    assert temporal_order_is_valid(train, validation, test)
    train_end, validation_end = temporal_split_bounds(5)
    assert train_end >= 1
    assert validation_end > train_end
    assert validation_end < 5


def test_temporal_leakage_detection():
    assert temporal_order_is_valid([1, 2], [3], [4])
    assert temporal_order_is_valid([1, 2], [2], [4])
    assert not temporal_order_is_valid([1, 5], [3], [4])
    assert not temporal_order_is_valid([1], [2, 5], [4])


def test_candidate_exclusion():
    assert exclude_train_items([10, 11, 12, 11], [11, 99]) == [10, 12]


def test_top_n_uniqueness():
    assert recommendations_are_unique([1, 2, 3])
    assert not recommendations_are_unique([1, 2, 1])


def test_null_and_duplicate_rows():
    assert has_null_or_duplicate([(1, None, 4.0)], [0, 1, 2])
    assert has_null_or_duplicate([(1, 2, 4.0), (1, 2, 4.0)], [0, 1])
    assert not has_null_or_duplicate([(1, 2, 4.0), (1, 3, 5.0)], [0, 1])


def test_schema_headers():
    assert schema_is_valid("ratings.csv", "userId,movieId,rating,timestamp")
    assert not schema_is_valid("ratings.csv", "userId,movieId,score")
    assert set(MOVIELENS_HEADERS) == {
        "ratings.csv",
        "movies.csv",
        "tags.csv",
        "links.csv",
        "genome-scores.csv",
        "genome-tags.csv",
    }
