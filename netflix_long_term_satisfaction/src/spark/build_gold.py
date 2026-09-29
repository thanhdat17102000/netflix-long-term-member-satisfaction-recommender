from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyspark.sql import functions as F

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
    spark = create_spark("MovieLens-Gold", config)
    silver = lake_path(config, "silver")
    gold = lake_path(config, "gold")
    partitions = int(config.get("spark_partitions", 4))

    train = spark.read.parquet(f"{silver}/user_train")
    validation = spark.read.parquet(f"{silver}/user_validation")
    test = spark.read.parquet(f"{silver}/user_test")
    movies = spark.read.parquet(f"{silver}/movies")

    user_features = train.groupBy("userId").agg(
        F.count("*").alias("user_rating_count"),
        F.avg("rating").alias("user_mean_rating"),
        F.min("timestamp").alias("train_first_timestamp"),
        F.max("timestamp").alias("train_last_timestamp"),
    ).withColumn(
        "user_activity_span_days",
        (F.col("train_last_timestamp") - F.col("train_first_timestamp")) / F.lit(86400.0),
    ).withColumn(
        "last_train_year",
        F.year(F.to_timestamp(F.from_unixtime("train_last_timestamp"))),
    ).withColumn(
        "last_train_month",
        F.month(F.to_timestamp(F.from_unixtime("train_last_timestamp"))),
    )

    popularity = train.groupBy("movieId").agg(
        F.count("*").alias("movie_rating_count"),
        F.avg("rating").alias("movie_mean_rating"),
    ).withColumn("movie_popularity", F.col("movie_rating_count"))

    movie_features = movies.join(popularity, "movieId", "left").fillna(
        {"movie_rating_count": 0, "movie_mean_rating": 0.0, "movie_popularity": 0}
    )

    drop_helper = ("row_number", "user_count", "train_end", "validation_end")
    for frame, name in (
        (train.drop(*[column for column in drop_helper if column in train.columns]), "train"),
        (validation.drop(*[column for column in drop_helper if column in validation.columns]), "validation"),
        (test.drop(*[column for column in drop_helper if column in test.columns]), "test"),
        (movie_features, "movie_features"),
        (user_features, "user_features"),
        (popularity.orderBy(F.desc("movie_rating_count"), F.desc("movie_mean_rating")), "popularity"),
    ):
        frame.repartition(partitions).write.mode("overwrite").parquet(f"{gold}/{name}")

    spark.stop()


if __name__ == "__main__":
    main()
