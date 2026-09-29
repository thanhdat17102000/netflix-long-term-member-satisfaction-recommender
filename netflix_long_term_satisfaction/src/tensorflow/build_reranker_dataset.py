from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.config import artifacts_dir, lake_path, load_config
from src.common.spark import create_spark


def _sanitize(name: str) -> str:
    return "genre_" + "".join(ch if ch.isalnum() else "_" for ch in str(name))


def _add_genre_features(frame: DataFrame, genres: list[str]) -> DataFrame:
    for genre in genres:
        frame = frame.withColumn(_sanitize(genre), F.array_contains("genres", F.lit(genre)).cast("int"))
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    spark = create_spark("MovieLens-Reranker-Features", config)
    silver = lake_path(config, "silver")
    gold = lake_path(config, "gold")
    partitions = int(config.get("spark_partitions", 4))
    threshold = float(config["positive_rating_threshold"])

    candidates = spark.read.parquet(f"{gold}/als_candidates")
    movies = spark.read.parquet(f"{gold}/movie_features")
    users = spark.read.parquet(f"{gold}/user_features")
    train = spark.read.parquet(f"{gold}/train")
    validation = spark.read.parquet(f"{gold}/validation")
    test = spark.read.parquet(f"{gold}/test")
    genome = spark.read.parquet(f"{silver}/genome_scores")

    train_movies = train.select("movieId").distinct()
    genome_train = genome.join(train_movies, "movieId", "inner")
    top_k = int(config["genome_top_k"])
    top_tags = (
        genome_train.groupBy("tagId")
        .agg(F.variance("relevance").alias("variance"))
        .orderBy(F.desc("variance"), F.asc("tagId"))
        .limit(top_k)
    )
    selected_tag_ids = [int(row.tagId) for row in top_tags.select("tagId").collect()]
    if selected_tag_ids:
        genome_selected = genome.join(top_tags.select("tagId"), "tagId", "inner")
        genome_wide = genome_selected.groupBy("movieId").pivot("tagId", selected_tag_ids).agg(F.max("relevance")).fillna(0.0)
        genome_cols = [column for column in genome_wide.columns if column != "movieId"]
        genome_wide = genome_wide.select(
            "movieId",
            *[F.col(column).alias(f"genome_{column}") for column in genome_cols],
        )
    else:
        genome_wide = movies.select("movieId").distinct()

    genre_rows = (
        train.join(movies.select("movieId", "genres"), "movieId", "inner")
        .select(F.explode("genres").alias("genre"))
        .filter(F.col("genre").isNotNull() & (F.col("genre") != ""))
        .distinct()
        .orderBy("genre")
        .collect()
    )
    genres = [row.genre for row in genre_rows]

    def make_features(labels: DataFrame) -> DataFrame:
        frame = (
            candidates.join(movies, "movieId", "left")
            .join(users, "userId", "left")
            .join(genome_wide, "movieId", "left")
            .join(labels, ["userId", "movieId"], "left")
            .withColumn("label", F.coalesce(F.col("label"), F.lit(0.0)))
            .withColumn("release_year", F.col("year"))
            .withColumn("recency_days", F.col("user_activity_span_days"))
            .withColumn("movie_age_years", F.col("last_train_year") - F.col("year"))
            .withColumn("temporal_last_ts", F.col("train_last_timestamp"))
        )
        frame = _add_genre_features(frame, genres)
        fill = {
            "label": 0.0,
            "movie_rating_count": 0,
            "movie_mean_rating": 0.0,
            "movie_popularity": 0,
            "als_score": 0.0,
            "release_year": 0,
            "recency_days": 0.0,
            "movie_age_years": 0.0,
            "user_rating_count": 0,
            "user_mean_rating": 0.0,
            "user_activity_span_days": 0.0,
            "temporal_last_ts": 0,
            "last_train_year": 0,
            "last_train_month": 0,
        }
        return frame.fillna(fill)

    validation_labels = validation.filter(F.col("rating") >= threshold).select("userId", "movieId").withColumn("label", F.lit(1.0))
    test_labels = test.filter(F.col("rating") >= threshold).select("userId", "movieId").withColumn("label", F.lit(1.0))
    make_features(validation_labels).repartition(partitions).write.mode("overwrite").parquet(f"{gold}/reranker_features")
    make_features(test_labels).repartition(partitions).write.mode("overwrite").parquet(f"{gold}/reranker_test_features")

    artifacts_dir(config, "models", "reranker").joinpath("genome_tag_ids.json").write_text(
        json.dumps({"method": "train_variance_topk", "tag_ids": selected_tag_ids, "genres": genres}, indent=2),
        encoding="utf-8",
    )
    spark.stop()


if __name__ == "__main__":
    main()
