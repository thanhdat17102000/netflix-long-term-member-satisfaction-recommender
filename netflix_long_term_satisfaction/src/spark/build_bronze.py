from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.config import lake_path, load_config
from src.common.spark import create_spark

RATINGS_SCHEMA = T.StructType(
    [
        T.StructField("userId", T.IntegerType(), True),
        T.StructField("movieId", T.IntegerType(), True),
        T.StructField("rating", T.DoubleType(), True),
        T.StructField("timestamp", T.LongType(), True),
    ]
)
MOVIES_SCHEMA = T.StructType(
    [
        T.StructField("movieId", T.IntegerType(), True),
        T.StructField("title", T.StringType(), True),
        T.StructField("genres", T.StringType(), True),
    ]
)
TAGS_SCHEMA = T.StructType(
    [
        T.StructField("userId", T.IntegerType(), True),
        T.StructField("movieId", T.IntegerType(), True),
        T.StructField("tag", T.StringType(), True),
        T.StructField("timestamp", T.LongType(), True),
    ]
)
LINKS_SCHEMA = T.StructType(
    [
        T.StructField("movieId", T.IntegerType(), True),
        T.StructField("imdbId", T.IntegerType(), True),
        T.StructField("tmdbId", T.IntegerType(), True),
    ]
)
GENOME_SCORES_SCHEMA = T.StructType(
    [
        T.StructField("movieId", T.IntegerType(), True),
        T.StructField("tagId", T.IntegerType(), True),
        T.StructField("relevance", T.DoubleType(), True),
    ]
)
GENOME_TAGS_SCHEMA = T.StructType(
    [
        T.StructField("tagId", T.IntegerType(), True),
        T.StructField("tag", T.StringType(), True),
    ]
)


def _write(frame: DataFrame, path: str, partitions: int, partition_by: str | None = None) -> None:
    if partition_by:
        # Hash by the partition column so each event_date lands in one task and one file.
        frame = frame.repartition(F.col(partition_by))
        writer = frame.write.mode("overwrite").partitionBy(partition_by)
    else:
        frame = frame.repartition(max(1, partitions))
        writer = frame.write.mode("overwrite")
    writer.parquet(path)


def _read_csv(spark, path: str, schema: T.StructType) -> DataFrame:
    return spark.read.schema(schema).option("header", True).csv(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    spark = create_spark("MovieLens-Bronze", config)
    raw = lake_path(config, "raw")
    bronze = lake_path(config, "bronze")
    quarantine = lake_path(config, "quarantine")
    partitions = int(config.get("spark_partitions", 4))

    ratings = _read_csv(spark, f"{raw}/ratings.csv", RATINGS_SCHEMA).withColumn(
        "event_ts", F.to_timestamp(F.from_unixtime("timestamp"))
    ).withColumn("event_date", F.to_date("event_ts"))
    rating_dupes = ratings.groupBy("userId", "movieId", "timestamp").count().filter(F.col("count") > 1)
    ratings_flagged = ratings.join(rating_dupes.select("userId", "movieId", "timestamp"), ["userId", "movieId", "timestamp"], "left_anti")
    ratings_bad = ratings.filter(
        F.col("userId").isNull()
        | F.col("movieId").isNull()
        | F.col("rating").isNull()
        | F.col("timestamp").isNull()
        | F.col("event_ts").isNull()
        | (F.col("rating") < F.lit(0.5))
        | (F.col("rating") > F.lit(5.0))
        | (F.col("timestamp") <= 0)
    ).unionByName(ratings.join(rating_dupes.select("userId", "movieId", "timestamp"), ["userId", "movieId", "timestamp"], "inner"), allowMissingColumns=True)
    ratings_good = ratings_flagged.filter(
        F.col("userId").isNotNull()
        & F.col("movieId").isNotNull()
        & F.col("rating").isNotNull()
        & F.col("timestamp").isNotNull()
        & F.col("event_ts").isNotNull()
        & F.col("rating").between(0.5, 5.0)
        & (F.col("timestamp") > 0)
    )
    _write(ratings_good, f"{bronze}/ratings", partitions, "event_date")
    _write(ratings_bad.withColumn("reason", F.lit("ratings_invalid_or_duplicate")), f"{quarantine}/ratings", max(1, partitions // 4 or 1))

    movies = _read_csv(spark, f"{raw}/movies.csv", MOVIES_SCHEMA)
    movies = movies.withColumn("year", F.regexp_extract("title", r"\((\d{4})\)\s*$", 1).cast("int"))
    movies = movies.withColumn(
        "genres_array",
        F.when(
            F.col("genres").isNull() | (F.trim(F.col("genres")) == "") | (F.col("genres") == "(no genres listed)"),
            F.array().cast("array<string>"),
        ).otherwise(F.split(F.col("genres"), r"\|")),
    )
    movies_bad = movies.filter(F.col("movieId").isNull() | F.col("title").isNull() | (F.size("genres_array") == 0))
    movies_good = movies.filter(F.col("movieId").isNotNull() & F.col("title").isNotNull() & (F.size("genres_array") > 0))
    movies_good = movies_good.withColumn("genres", F.col("genres_array")).drop("genres_array")
    movies_bad = movies_bad.withColumn("reason", F.lit("movie_missing_metadata_or_empty_genre"))
    _write(movies_good, f"{bronze}/movies", partitions)
    _write(movies_bad, f"{quarantine}/movies", max(1, partitions // 4 or 1))

    tags = _read_csv(spark, f"{raw}/tags.csv", TAGS_SCHEMA)
    tags_bad = tags.filter(F.col("userId").isNull() | F.col("movieId").isNull() | F.col("tag").isNull() | F.col("timestamp").isNull())
    tags_good = tags.join(
        tags_bad.select("userId", "movieId", "tag", "timestamp"),
        ["userId", "movieId", "tag", "timestamp"],
        "left_anti",
    ).dropDuplicates(["userId", "movieId", "tag", "timestamp"])
    _write(tags_good, f"{bronze}/tags", partitions)
    _write(tags_bad.withColumn("reason", F.lit("tags_null")), f"{quarantine}/tags", max(1, partitions // 4 or 1))

    links = _read_csv(spark, f"{raw}/links.csv", LINKS_SCHEMA)
    links_bad = links.filter(F.col("movieId").isNull())
    links_good = links.filter(F.col("movieId").isNotNull()).dropDuplicates(["movieId"])
    _write(links_good, f"{bronze}/links", partitions)
    _write(links_bad.withColumn("reason", F.lit("links_null_movie")), f"{quarantine}/links", max(1, partitions // 4 or 1))

    genome_tags = _read_csv(spark, f"{raw}/genome-tags.csv", GENOME_TAGS_SCHEMA)
    genome_scores = _read_csv(spark, f"{raw}/genome-scores.csv", GENOME_SCORES_SCHEMA)
    genome_bad = genome_scores.filter(
        F.col("movieId").isNull()
        | F.col("tagId").isNull()
        | F.col("relevance").isNull()
        | (F.col("relevance") < 0)
        | (F.col("relevance") > 1)
    )
    genome_missing_tag = genome_scores.join(genome_tags.select("tagId"), "tagId", "left_anti")
    genome_quarantine = genome_bad.unionByName(genome_missing_tag, allowMissingColumns=True).dropDuplicates()
    genome_good = genome_scores.join(genome_quarantine.select("movieId", "tagId"), ["movieId", "tagId"], "left_anti")
    genome_good = genome_good.join(genome_tags.select("tagId"), "tagId", "inner")
    _write(genome_good, f"{bronze}/genome_scores", partitions)
    _write(genome_tags.dropna(), f"{bronze}/genome_tags", max(1, partitions // 4 or 1))
    _write(genome_quarantine.withColumn("reason", F.lit("genome_invalid_or_missing_tag")), f"{quarantine}/genome_scores", max(1, partitions // 4 or 1))
    spark.stop()


if __name__ == "__main__":
    main()
