from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyspark.ml.recommendation import ALSModel
from pyspark.sql import functions as F
from pyspark.sql.window import Window

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.config import lake_path, load_config
from src.common.spark import create_spark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    spark = create_spark("MovieLens-Candidates", config)
    gold = lake_path(config, "gold")
    partitions = int(config.get("spark_partitions", 4))
    top_n = int(config["als_top_n"])

    model = ALSModel.load(f"{gold}/models/als")
    users = spark.read.parquet(f"{gold}/user_features").select("userId").distinct()
    train = spark.read.parquet(f"{gold}/train").select("userId", "movieId")
    raw = model.recommendForUserSubset(users, max(top_n * 2, top_n))
    candidates = raw.select("userId", F.explode("recommendations").alias("rec")).select(
        "userId",
        F.col("rec.movieId").alias("movieId"),
        F.col("rec.rating").alias("als_score"),
    )
    candidates = candidates.join(train, ["userId", "movieId"], "left_anti")
    window = Window.partitionBy("userId").orderBy(F.desc("als_score"), F.asc("movieId"))
    candidates = (
        candidates.dropDuplicates(["userId", "movieId"])
        .withColumn("rank", F.row_number().over(window))
        .filter(F.col("rank") <= top_n)
        .select("userId", "movieId", "rank", "als_score")
    )
    candidates.repartition(partitions).write.mode("overwrite").parquet(f"{gold}/als_candidates")
    spark.stop()


if __name__ == "__main__":
    main()
