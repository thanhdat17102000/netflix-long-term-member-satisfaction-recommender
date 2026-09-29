from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    spark = create_spark("MovieLens-Silver", config)
    bronze = lake_path(config, "bronze")
    silver = lake_path(config, "silver")
    partitions = int(config.get("spark_partitions", 4))
    min_split = int(config.get("min_split_interactions", 3))
    train_ratio = float(config.get("train_ratio", 0.8))
    validation_ratio = float(config.get("validation_ratio", 0.1))

    ratings = spark.read.parquet(f"{bronze}/ratings")
    movies = spark.read.parquet(f"{bronze}/movies")
    genome = spark.read.parquet(f"{bronze}/genome_scores")

    stats = ratings.groupBy("userId").agg(
        F.count("*").alias("rating_count"),
        F.min("timestamp").alias("first_timestamp"),
        F.max("timestamp").alias("last_timestamp"),
        F.avg("rating").alias("mean_rating"),
    ).withColumn("activity_span_days", (F.col("last_timestamp") - F.col("first_timestamp")) / F.lit(86400.0))

    long_term = stats.filter(
        (F.col("rating_count") >= F.lit(int(config["long_term_min_ratings"])))
        & (F.col("activity_span_days") >= F.lit(float(config["long_term_min_days"])))
    )
    eligible = long_term.filter(F.col("rating_count") >= F.lit(min_split))

    ordered = ratings.join(eligible.select("userId"), "userId").withColumn(
        "row_number", F.row_number().over(Window.partitionBy("userId").orderBy("timestamp", "movieId"))
    ).withColumn("user_count", F.count("*").over(Window.partitionBy("userId")))

    train_end = F.greatest(
        F.lit(1),
        F.least((F.col("user_count") * F.lit(train_ratio)).cast("int"), F.col("user_count") - F.lit(2)),
    )
    validation_end = F.greatest(
        train_end + F.lit(1),
        F.least((F.col("user_count") * F.lit(train_ratio + validation_ratio)).cast("int"), F.col("user_count") - F.lit(1)),
    )
    split = ordered.withColumn("train_end", train_end).withColumn("validation_end", validation_end)
    train = split.filter(F.col("row_number") <= F.col("train_end"))
    validation = split.filter((F.col("row_number") > F.col("train_end")) & (F.col("row_number") <= F.col("validation_end")))
    test = split.filter(F.col("row_number") > F.col("validation_end"))

    train_bounds = train.groupBy("userId").agg(F.max("timestamp").alias("max_train_ts"))
    val_bounds = validation.groupBy("userId").agg(
        F.min("timestamp").alias("min_val_ts"),
        F.max("timestamp").alias("max_val_ts"),
        F.count("*").alias("val_count"),
    )
    test_bounds = test.groupBy("userId").agg(F.min("timestamp").alias("min_test_ts"), F.count("*").alias("test_count"))
    leak_check = train_bounds.join(val_bounds, "userId").join(test_bounds, "userId")
    leaks = leak_check.filter(
        (F.col("val_count") == 0)
        | (F.col("test_count") == 0)
        | (F.col("max_train_ts") >= F.col("min_val_ts"))
        | (F.col("max_val_ts") >= F.col("min_test_ts"))
    )
    leak_count = leaks.limit(1).count()
    if leak_count:
        sample = leaks.limit(5).toJSON().collect()
        raise ValueError(f"Dữ liệu chia theo thời gian bị trống hoặc sai thứ tự: {sample}")

    for frame, name in (
        (ratings, "ratings"),
        (movies, "movies"),
        (genome, "genome_scores"),
        (stats, "user_stats"),
        (long_term, "long_term_users"),
        (train.drop("train_end", "validation_end"), "user_train"),
        (validation.drop("train_end", "validation_end"), "user_validation"),
        (test.drop("train_end", "validation_end"), "user_test"),
    ):
        frame.repartition(partitions).write.mode("overwrite").parquet(f"{silver}/{name}")

    spark.stop()


if __name__ == "__main__":
    main()
