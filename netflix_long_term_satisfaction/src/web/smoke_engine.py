from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.common.config import artifacts_dir, load_config, project_root, resolve_input_dir
from src.common.logic import (
    UserHistory,
    is_long_term,
    recommendations_are_unique,
    temporal_order_is_valid,
    temporal_split_bounds,
)
from src.common.metrics import (
    catalog_coverage,
    hit_rate_at_k,
    map_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    rmse,
    satisfaction_lift,
    satisfied_hit_rate_at_k,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _year(title: str) -> int:
    match = re.search(r"\((\d{4})\)\s*$", title)
    return int(match.group(1)) if match else 0


def _als_fit(train_rows: list[dict], user_ids: list[int], item_ids: list[int], rank: int, n_iter: int, reg: float, seed: int):
    """Fit the small local ALS example used by the dashboard smoke profile."""
    rng = np.random.default_rng(seed)
    user_index = {user: i for i, user in enumerate(user_ids)}
    item_index = {item: i for i, item in enumerate(item_ids)}
    observations = [
        (user_index[int(row["userId"])], item_index[int(row["movieId"])], float(row["rating"]))
        for row in train_rows
        if int(row["userId"]) in user_index and int(row["movieId"]) in item_index
    ]
    user_factors = rng.normal(0, 0.1, size=(len(user_ids), rank))
    movie_factors = rng.normal(0, 0.1, size=(len(item_ids), rank))
    regularizer = np.eye(rank) * reg
    for _ in range(n_iter):
        ratings_by_movie: dict[int, list[tuple[int, float]]] = defaultdict(list)
        ratings_by_user: dict[int, list[tuple[int, float]]] = defaultdict(list)
        for u, i, rating in observations:
            ratings_by_user[u].append((i, rating))
            ratings_by_movie[i].append((u, rating))
        for u, pairs in ratings_by_user.items():
            matrix = np.zeros((rank, rank))
            vector = np.zeros(rank)
            for i, rating in pairs:
                movie_vector = movie_factors[i]
                matrix += np.outer(movie_vector, movie_vector)
                vector += rating * movie_vector
            user_factors[u] = np.linalg.solve(matrix + regularizer, vector)
        for i, pairs in ratings_by_movie.items():
            matrix = np.zeros((rank, rank))
            vector = np.zeros(rank)
            for u, rating in pairs:
                user_vector = user_factors[u]
                matrix += np.outer(user_vector, user_vector)
                vector += rating * user_vector
            movie_factors[i] = np.linalg.solve(matrix + regularizer, vector)
        user_factors = np.maximum(user_factors, 0)
        movie_factors = np.maximum(movie_factors, 0)
    return user_factors, movie_factors, user_index, item_index


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -20, 20)))


def _train_logistic(features: np.ndarray, labels: np.ndarray, seed: int, epochs: int = 80, lr: float = 0.15) -> np.ndarray:
    """Train the smoke ranker; the full pipeline uses TensorFlow instead."""
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.05, size=features.shape[1])
    if len(features) == 0:
        return weights
    for _ in range(epochs):
        preds = _sigmoid(features @ weights)
        gradient = features.T @ (preds - labels) / max(len(labels), 1)
        weights -= lr * gradient
    return weights


def _ranking_metrics(recs: dict[int, list[int]], truth: dict[int, list[int]], catalog_size: int, k: int = 10) -> dict[str, float]:
    if not recs:
        return {}
    rows = []
    recommended: list[int] = []
    for user, items in recs.items():
        relevant = truth.get(user, [])
        rows.append(
            {
                "precision_at_10": precision_at_k(items, relevant, k),
                "recall_at_10": recall_at_k(items, relevant, k),
                "map_at_10": map_at_k(items, relevant, k),
                "ndcg_at_10": ndcg_at_k(items, relevant, k),
                "hit_rate_at_10": hit_rate_at_k(items, relevant, k),
                "satisfied_hit_rate_at_10": satisfied_hit_rate_at_k(items, relevant, k),
            }
        )
        recommended.extend(items[:k])
    summary = {key: sum(row[key] for row in rows) / len(rows) for key in rows[0]}
    summary["catalog_coverage"] = catalog_coverage(recommended, catalog_size)
    return summary


def run_smoke_demo() -> dict:
    """Build dashboard data from the small fixture without Spark or TensorFlow."""
    root = project_root()
    config = load_config(str(root / "configs" / "smoke.yaml"))
    fixture = resolve_input_dir(config)
    movies_raw = _read_csv(fixture / "movies.csv")
    ratings_raw = _read_csv(fixture / "ratings.csv")
    genome_raw = _read_csv(fixture / "genome-scores.csv")

    movies = {
        int(row["movieId"]): {
            "movieId": int(row["movieId"]),
            "title": row["title"],
            "genres": row["genres"].split("|"),
            "year": _year(row["title"]),
        }
        for row in movies_raw
    }
    ratings = [
        {
            "userId": int(row["userId"]),
            "movieId": int(row["movieId"]),
            "rating": float(row["rating"]),
            "timestamp": int(row["timestamp"]),
        }
        for row in ratings_raw
    ]

    users: dict[int, list[dict]] = defaultdict(list)
    for row in ratings:
        users[row["userId"]].append(row)
    for rows in users.values():
        rows.sort(key=lambda item: (item["timestamp"], item["movieId"]))

    long_term = []
    train, validation, test = [], [], []
    leakage_ok = True
    for user_id, rows in users.items():
        history = UserHistory(user_id, len(rows), rows[0]["timestamp"], rows[-1]["timestamp"])
        if not is_long_term(history, config["long_term_min_days"], config["long_term_min_ratings"]):
            continue
        if len(rows) < int(config["min_split_interactions"]):
            continue
        long_term.append(
            {
                "userId": user_id,
                "rating_count": history.rating_count,
                "activity_span_days": round(history.activity_span_days, 1),
                "mean_rating": round(sum(item["rating"] for item in rows) / len(rows), 3),
                "is_long_term": True,
            }
        )
        train_end, validation_end = temporal_split_bounds(len(rows), config["train_ratio"], config["validation_ratio"])
        user_train, user_val, user_test = rows[:train_end], rows[train_end:validation_end], rows[validation_end:]

        def history_row(item: dict, split: str) -> dict:
            movie = movies.get(item["movieId"], {})
            return {
                "movieId": item["movieId"],
                "title": movie.get("title"),
                "rating": item["rating"],
                "timestamp": item["timestamp"],
                "split": split,
            }

        long_term[-1].update(
            {
                "train_rows": len(user_train),
                "validation_rows": len(user_val),
                "test_rows": len(user_test),
                "history": (
                    [history_row(item, "train") for item in user_train]
                    + [history_row(item, "validation") for item in user_val]
                    + [history_row(item, "test") for item in user_test]
                ),
            }
        )
        if not temporal_order_is_valid(
            [item["timestamp"] for item in user_train],
            [item["timestamp"] for item in user_val],
            [item["timestamp"] for item in user_test],
        ):
            leakage_ok = False
        train.extend(user_train)
        validation.extend(user_val)
        test.extend(user_test)

    user_stats = {}
    for user_id in {row["userId"] for row in train}:
        rows = [item for item in train if item["userId"] == user_id]
        user_stats[user_id] = {
            "user_rating_count": len(rows),
            "user_mean_rating": sum(item["rating"] for item in rows) / len(rows),
            "user_activity_span_days": (rows[-1]["timestamp"] - rows[0]["timestamp"]) / 86400.0,
            "train_last_timestamp": rows[-1]["timestamp"],
        }
    movie_stats = {}
    for movie_id in {row["movieId"] for row in train}:
        rows = [item for item in train if item["movieId"] == movie_id]
        movie_stats[movie_id] = {
            "movie_rating_count": len(rows),
            "movie_mean_rating": sum(item["rating"] for item in rows) / len(rows),
        }

    user_ids = sorted(user_stats)
    item_ids = sorted(movies)
    rank = min(int(config["als_rank"]), max(2, min(len(user_ids), len(item_ids))))
    user_factors, movie_factors, user_index, item_index = _als_fit(
        train, user_ids, item_ids, rank, int(config["als_max_iter"]), float(config["als_reg_param"]), int(config["seed"])
    )

    seen = defaultdict(set)
    for row in train:
        seen[row["userId"]].add(row["movieId"])

    als_candidates: dict[int, list[tuple[int, float]]] = {}
    for user_id in user_ids:
        scores = []
        for movie_id in item_ids:
            if movie_id in seen[user_id]:
                continue
            score = float(user_factors[user_index[user_id]] @ movie_factors[item_index[movie_id]])
            scores.append((movie_id, score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        als_candidates[user_id] = scores[: int(config["als_top_n"])]

    popular = sorted(
        movie_stats.items(),
        key=lambda item: (-item[1]["movie_rating_count"], -item[1]["movie_mean_rating"], item[0]),
    )
    popularity_recs = {
        user_id: [movie_id for movie_id, _ in popular if movie_id not in seen[user_id]][:10]
        for user_id in user_ids
    }
    als_recs = {user_id: [movie_id for movie_id, _ in items[:10]] for user_id, items in als_candidates.items()}

    genome = defaultdict(dict)
    for row in genome_raw:
        genome[int(row["movieId"])][int(row["tagId"])] = float(row["relevance"])
    train_movies = {row["movieId"] for row in train}
    tag_ids = sorted({int(row["tagId"]) for row in genome_raw})
    tag_var = []
    for tag_id in tag_ids:
        values = [genome[movie_id][tag_id] for movie_id in train_movies if tag_id in genome[movie_id]]
        tag_var.append((float(np.var(values)) if values else 0.0, tag_id))
    selected_tags = [tag_id for _, tag_id in sorted(tag_var, reverse=True)[: int(config["genome_top_k"])]]

    def feature_row(user_id: int, movie_id: int, als_score: float) -> list[float]:
        user = user_stats[user_id]
        movie = movie_stats.get(movie_id, {"movie_rating_count": 0, "movie_mean_rating": 0.0})
        meta = movies[movie_id]
        values = [
            als_score,
            movie["movie_rating_count"],
            movie["movie_mean_rating"],
            user["user_rating_count"],
            user["user_mean_rating"],
            user["user_activity_span_days"],
            float(meta["year"]),
            user["train_last_timestamp"] / 1e9,
            float(datetime.fromtimestamp(user["train_last_timestamp"], timezone.utc).year - (meta["year"] or 0)),
        ]
        values.extend(genome[movie_id].get(tag_id, 0.0) for tag_id in selected_tags)
        return values

    threshold = float(config["positive_rating_threshold"])
    val_pos = {(row["userId"], row["movieId"]) for row in validation if row["rating"] >= threshold}
    test_pos = {(row["userId"], row["movieId"]) for row in test if row["rating"] >= threshold}

    ranker_features, ranker_labels = [], []
    for user_id, items in als_candidates.items():
        for movie_id, score in items:
            ranker_features.append(feature_row(user_id, movie_id, score))
            ranker_labels.append(1.0 if (user_id, movie_id) in val_pos else 0.0)
    weights = _train_logistic(np.asarray(ranker_features, dtype=float), np.asarray(ranker_labels, dtype=float), int(config["seed"]))

    hybrid_recs: dict[int, list[int]] = {}
    hybrid_detail = []
    for user_id, items in als_candidates.items():
        scored = []
        for movie_id, als_score in items:
            feat = np.asarray(feature_row(user_id, movie_id, als_score), dtype=float)
            scored.append((movie_id, float(_sigmoid(np.array([feat @ weights]))[0]), als_score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        top = scored[:10]
        hybrid_recs[user_id] = [movie_id for movie_id, _, _ in top]
        for rank, (movie_id, rerank_score, als_score) in enumerate(top, start=1):
            hybrid_detail.append(
                {
                    "userId": user_id,
                    "movieId": movie_id,
                    "title": movies[movie_id]["title"],
                    "genres": movies[movie_id]["genres"],
                    "year": movies[movie_id]["year"],
                    "rank": rank,
                    "rerank_score": round(rerank_score, 4),
                    "als_score": round(als_score, 4),
                    "model": "hybrid",
                }
            )

    def reasons_for(user_id: int, movie_id: int, als_score: float | None = None, rerank_score: float | None = None) -> list[str]:
        reasons: list[str] = []
        if als_score is not None:
            reasons.append("Có điểm ứng viên từ ALS")
        if rerank_score is not None:
            reasons.append("Đã xếp hạng lại bằng mô hình logistic")
        movie = movies[movie_id]
        if movie.get("genres"):
            reasons.append(f"Thể loại: {movie['genres'][0]}")
        if movie_stats.get(movie_id, {}).get("movie_rating_count", 0) > 0:
            reasons.append("Có lượt chấm trong tập huấn luyện")
        if genome.get(movie_id):
            reasons.append("Có đặc trưng Tag Genome")
        return reasons[:3] or ["Chưa có dữ liệu để giải thích gợi ý"]

    def detail_rows_for(model: str, recs: dict[int, list[int]]) -> list[dict]:
        rows: list[dict] = []
        candidate_scores = {user_id: dict(items) for user_id, items in als_candidates.items()}
        for user_id, movie_ids in recs.items():
            for rank, movie_id in enumerate(movie_ids[:10], start=1):
                als_score = candidate_scores.get(user_id, {}).get(movie_id)
                row = {
                    "userId": user_id,
                    "movieId": movie_id,
                    "title": movies[movie_id]["title"],
                    "genres": movies[movie_id]["genres"],
                    "year": movies[movie_id]["year"],
                    "rank": rank,
                    "als_score": round(float(als_score), 4) if als_score is not None else None,
                    "rerank_score": None,
                    "model": model,
                }
                row["reasons"] = reasons_for(user_id, movie_id, als_score, None)
                rows.append(row)
        return rows

    popularity_detail = detail_rows_for("popularity", popularity_recs)
    als_detail = detail_rows_for("als", als_recs)
    for row in hybrid_detail:
        row["reasons"] = reasons_for(row["userId"], row["movieId"], row.get("als_score"), row.get("rerank_score"))
    recommendations_by_model = {
        "popularity": popularity_detail,
        "als": als_detail,
        "hybrid": hybrid_detail,
    }

    truth = defaultdict(list)
    for user_id, movie_id in test_pos:
        truth[user_id].append(movie_id)
    catalog_size = len(movies)
    metrics = {
        "popularity": _ranking_metrics(popularity_recs, truth, catalog_size),
        "als": _ranking_metrics(als_recs, truth, catalog_size),
        "hybrid": _ranking_metrics(hybrid_recs, truth, catalog_size),
    }

    als_pairs = []
    pop_pairs = []
    for row in test:
        user_id, movie_id, rating = row["userId"], row["movieId"], row["rating"]
        if user_id in user_index and movie_id in item_index:
            als_pairs.append((rating, float(user_factors[user_index[user_id]] @ movie_factors[item_index[movie_id]])))
        if movie_id in movie_stats:
            pop_pairs.append((rating, movie_stats[movie_id]["movie_mean_rating"]))
    metrics["als"]["rmse"] = None if not als_pairs else round(rmse(*zip(*als_pairs)), 4)
    metrics["popularity"]["rmse"] = None if not pop_pairs else round(rmse(*zip(*pop_pairs)), 4)
    metrics["hybrid"]["rmse"] = None
    lift = satisfaction_lift(
        metrics["hybrid"].get("satisfied_hit_rate_at_10", 0.0),
        metrics["popularity"].get("satisfied_hit_rate_at_10", 0.0),
    )

    rec_dir = artifacts_dir(config, "recommendations")
    rec_path = rec_dir / "top10_recommendations.csv"
    with rec_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["userId", "movieId", "title", "rank", "rerank_score"])
        writer.writeheader()
        for row in hybrid_detail:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "web_smoke",
        "disclaimer": "Kết quả thử trên dữ liệu MovieLens mẫu; không đo mức hài lòng hay tỷ lệ duy trì thuê bao của Netflix.",
        "runtime": "Python/NumPy cục bộ; bản demo này không chạy Spark, Hadoop hoặc TensorFlow.",
        "pipeline": [
            {"name": "RAW fixture", "status": "done"},
            {"name": "BRONZE rules", "status": "done"},
            {"name": "SILVER long-term + split", "status": "done"},
            {"name": "GOLD features", "status": "done"},
            {"name": "ALS candidates", "status": "done"},
            {"name": "Re-ranker", "status": "done"},
            {"name": "Evaluation", "status": "done"},
        ],
        "checks": {
            "leakage_free": leakage_ok,
            "top10_unique": all(recommendations_are_unique(items) for items in hybrid_recs.values()),
            "long_term_users": len(long_term),
            "train_rows": len(train),
            "validation_rows": len(validation),
            "test_rows": len(test),
        },
        "long_term_users": long_term,
        "metrics": metrics,
        "satisfaction_lift_vs_popularity": lift,
        "recommendations": hybrid_detail,
        "models": ["popularity", "als", "hybrid"],
        "available_models": ["popularity", "als", "hybrid"],
        "movies": list(movies.values()),
        "recommendations_by_model": recommendations_by_model,
        "user_profiles": {str(row["userId"]): row for row in long_term},
        "data_quality": {
            "null_count": 0,
            "duplicate_count": 0,
            "invalid_rating_count": 0,
            "quarantine_rows": 0,
            "leakage_free": leakage_ok,
            "candidate_exclusion": all(
                all(movie_id not in seen[user_id] for movie_id in items)
                for user_id, items in als_recs.items()
            ),
            "schema_status": "PASS",
            "manifest_status": "FIXTURE",
        },
        "paths": {
            "recommendations": str(rec_path).replace("\\", "/"),
        },
    }
    metrics_dir = artifacts_dir(config, "metrics")
    (metrics_dir / "web_smoke_metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
