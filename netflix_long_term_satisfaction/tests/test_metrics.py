from src.common.metrics import (
    catalog_coverage,
    hit_rate_at_k,
    map_at_k,
    metric_in_unit_interval,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    rmse,
    satisfaction_lift,
    satisfied_hit_rate_at_k,
)


def test_ranking_metrics():
    recs = [1, 2, 3, 4]
    truth = [2, 4]
    assert precision_at_k(recs, truth, 2) == 0.5
    assert recall_at_k(recs, truth, 2) == 0.5
    assert hit_rate_at_k(recs, truth, 2) == 1.0
    assert 0 < ndcg_at_k(recs, truth, 4) <= 1
    assert 0 < map_at_k(recs, truth, 4) <= 1
    assert satisfied_hit_rate_at_k(recs, truth, 4) == 1.0


def test_metric_range():
    recs = [1, 2, 3]
    truth = [9]
    values = [
        precision_at_k(recs, truth, 10),
        recall_at_k(recs, truth, 10),
        map_at_k(recs, truth, 10),
        ndcg_at_k(recs, truth, 10),
        hit_rate_at_k(recs, truth, 10),
        catalog_coverage(recs, 10),
        satisfied_hit_rate_at_k(recs, truth, 10),
    ]
    assert all(metric_in_unit_interval(value) for value in values)


def test_rmse_and_lift():
    assert rmse([1.0, 3.0], [1.0, 3.0]) == 0.0
    assert satisfaction_lift(0.4, 0.2) == 1.0
    assert satisfaction_lift(0.2, 0.0) == 0.0
