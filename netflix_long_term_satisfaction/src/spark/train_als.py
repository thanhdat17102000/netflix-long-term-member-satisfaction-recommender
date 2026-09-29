from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.config import artifacts_dir, lake_path, load_config
from src.common.spark import create_spark


def _rmse(model, frame, evaluator: RegressionEvaluator) -> float | None:
    if frame.limit(1).count() == 0:
        return None
    scored = model.transform(frame.select("userId", "movieId", "rating")).na.drop(subset=["prediction"])
    if scored.limit(1).count() == 0:
        return None
    value = float(evaluator.evaluate(scored))
    return value if math.isfinite(value) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    spark = create_spark("MovieLens-ALS", config)
    gold = lake_path(config, "gold")
    train = spark.read.parquet(f"{gold}/train").select("userId", "movieId", "rating")
    model = ALS(
        rank=int(config["als_rank"]),
        regParam=float(config["als_reg_param"]),
        maxIter=int(config["als_max_iter"]),
        nonnegative=True,
        implicitPrefs=False,
        userCol="userId",
        itemCol="movieId",
        ratingCol="rating",
        coldStartStrategy="drop",
        seed=int(config["seed"]),
    ).fit(train)
    model.write().overwrite().save(f"{gold}/models/als")

    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    metrics = {
        "train_rmse": _rmse(model, train, evaluator),
        "validation_rmse": _rmse(model, spark.read.parquet(f"{gold}/validation"), evaluator),
        "test_rmse": _rmse(model, spark.read.parquet(f"{gold}/test"), evaluator),
        "rank": int(config["als_rank"]),
        "regParam": float(config["als_reg_param"]),
        "maxIter": int(config["als_max_iter"]),
        "nonnegative": True,
        "implicitPrefs": False,
        "seed": int(config["seed"]),
    }
    output = artifacts_dir(config, "metrics")
    (output / "als_rmse.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics))
    spark.stop()


if __name__ == "__main__":
    main()
