from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.config import artifacts_dir, lake_path, load_config
from src.common.metrics import (
    catalog_coverage,
    hit_rate_at_k,
    map_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    satisfaction_lift,
    satisfied_hit_rate_at_k,
)
from src.common.spark import create_spark


def _grouped_lists(frame: DataFrame, item_col: str = "movieId") -> dict[int, list[int]]:
    aggregated = (
        frame.groupBy("userId")
        .agg(F.sort_array(F.collect_list(F.struct("rank", item_col))).alias("items"))
        .select("userId", "items")
    )
    return {
        int(row.userId): [int(item[item_col]) for item in row.items]
        for row in aggregated.toLocalIterator()
    }


def _truth_lists(frame: DataFrame) -> dict[int, list[int]]:
    aggregated = frame.groupBy("userId").agg(F.collect_set("movieId").alias("items"))
    return {int(row.userId): [int(item) for item in row.items] for row in aggregated.toLocalIterator()}


def _ranking_metrics(recs: dict[int, list[int]], truth: dict[int, list[int]], catalog_size: int, k: int = 10) -> dict[str, float]:
    if not recs:
        return {}
    values = []
    recommended_items: list[int] = []
    for user, items in recs.items():
        relevant = truth.get(user, [])
        values.append(
            {
                "precision_at_10": precision_at_k(items, relevant, k),
                "recall_at_10": recall_at_k(items, relevant, k),
                "map_at_10": map_at_k(items, relevant, k),
                "ndcg_at_10": ndcg_at_k(items, relevant, k),
                "hit_rate_at_10": hit_rate_at_k(items, relevant, k),
                "satisfied_hit_rate_at_10": satisfied_hit_rate_at_k(items, relevant, k),
            }
        )
        recommended_items.extend(items[:k])
    summary = {key: sum(row[key] for row in values) / len(values) for key in values[0]}
    summary["catalog_coverage"] = catalog_coverage(recommended_items, catalog_size)
    return summary


def _popularity_recs(spark, gold: str, top_pool: int = 500) -> DataFrame:
    users = spark.read.parquet(f"{gold}/user_features").select("userId").distinct()
    popular = spark.read.parquet(f"{gold}/popularity").orderBy(
        F.desc("movie_rating_count"), F.desc("movie_mean_rating"), F.asc("movieId")
    ).limit(top_pool)
    train = spark.read.parquet(f"{gold}/train").select("userId", "movieId")
    window = Window.partitionBy("userId").orderBy(F.desc("movie_rating_count"), F.desc("movie_mean_rating"), F.asc("movieId"))
    return (
        users.crossJoin(F.broadcast(popular))
        .join(train, ["userId", "movieId"], "left_anti")
        .withColumn("rank", F.row_number().over(window))
        .filter(F.col("rank") <= 10)
        .select("userId", "movieId", "rank")
    )


def _spark_rmse(frame: DataFrame, pred_col: str) -> float | None:
    scored = frame.na.drop(subset=["rating", pred_col])
    if scored.limit(1).count() == 0:
        return None
    value = scored.select(F.sqrt(F.avg(F.pow(F.col("rating") - F.col(pred_col), 2)))).first()[0]
    if value is None or not math.isfinite(float(value)):
        return None
    return float(value)


def _write_figure(metrics: dict[str, dict[str, float]], path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("Cần matplotlib để tạo metric_comparison.png. Cài bằng: pip install matplotlib>=3.7") from exc

    models = [name for name in ("popularity", "als", "hybrid") if name in metrics]
    keys = [
        "precision_at_10",
        "recall_at_10",
        "map_at_10",
        "ndcg_at_10",
        "hit_rate_at_10",
        "satisfied_hit_rate_at_10",
        "catalog_coverage",
    ]
    x = list(range(len(keys)))
    width = 0.25
    figure, axis = plt.subplots(figsize=(12, 5))
    for index, model in enumerate(models):
        axis.bar(
            [value + (index - 1) * width for value in x],
            [float(metrics[model].get(key, 0.0) or 0.0) for key in keys],
            width=width,
            label=model,
        )
    axis.set_xticks(x, keys, rotation=25, ha="right")
    axis.set_ylim(0, 1.05)
    axis.set_ylabel("Giá trị chỉ số")
    axis.set_title("Đánh giá ngoại tuyến trên MovieLens")
    axis.legend()
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=140)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    spark = create_spark("MovieLens-Evaluation", config)
    gold = lake_path(config, "gold")
    threshold = float(config["positive_rating_threshold"])

    catalog_size = int(spark.read.parquet(f"{gold}/movie_features").select("movieId").distinct().count())
    test_all = spark.read.parquet(f"{gold}/test").select("userId", "movieId", "rating")
    test_positive = test_all.filter(F.col("rating") >= threshold)
    truth = _truth_lists(test_positive)

    popularity = _popularity_recs(spark, gold)
    als = spark.read.parquet(f"{gold}/als_candidates").filter(F.col("rank") <= 10).select("userId", "movieId", "rank")
    hybrid = spark.read.parquet(f"{gold}/reranked_recommendations").select("userId", "movieId", "rank")

    recs = {
        "popularity": _grouped_lists(popularity),
        "als": _grouped_lists(als),
        "hybrid": _grouped_lists(hybrid),
    }
    metrics = {name: _ranking_metrics(items, truth, catalog_size) for name, items in recs.items()}

    als_rmse_path = artifacts_dir(config, "metrics") / "als_rmse.json"
    als_rmse = None
    if als_rmse_path.is_file():
        payload = json.loads(als_rmse_path.read_text(encoding="utf-8"))
        als_rmse = payload.get("test_rmse", payload.get("validation_rmse"))
    pop_rmse = _spark_rmse(test_all.join(spark.read.parquet(f"{gold}/popularity").select("movieId", "movie_mean_rating"), "movieId"), "movie_mean_rating")
    metrics["popularity"]["rmse"] = pop_rmse
    metrics["als"]["rmse"] = als_rmse
    metrics["hybrid"]["rmse"] = None

    lift = satisfaction_lift(
        float(metrics["hybrid"].get("satisfied_hit_rate_at_10", 0.0)),
        float(metrics["popularity"].get("satisfied_hit_rate_at_10", 0.0)),
    )
    output = {
        "profile": config.get("profile"),
        "k": 10,
        "positive_rating_threshold": threshold,
        "catalog_size": catalog_size,
        "user_count": {
            name: len(items) for name, items in recs.items()
        },
        "models": metrics,
        "satisfaction_lift_vs_popularity": lift,
        "note": "Offline MovieLens proxy metrics. Not Netflix satisfaction or retention.",
    }

    metrics_dir = artifacts_dir(config, "metrics")
    json_path = metrics_dir / "metrics.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    csv_path = metrics_dir / "metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "metric", "value"])
        writer.writeheader()
        for model, values in metrics.items():
            for metric, value in values.items():
                writer.writerow({"model": model, "metric": metric, "value": value})
        writer.writerow({"model": "hybrid", "metric": "satisfaction_lift_vs_popularity", "value": lift})

    figure_path = artifacts_dir(config, "figures") / "metric_comparison.png"
    _write_figure(metrics, figure_path)
    spark.stop()
    print(f"Đã lưu {json_path}")
    print(f"Đã lưu {csv_path}")
    print(f"Đã lưu {figure_path}")


if __name__ == "__main__":
    main()
