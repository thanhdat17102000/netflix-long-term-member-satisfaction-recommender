from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.common.config import artifacts_dir, load_config, project_root, resolve_input_dir
from src.web.smoke_engine import run_smoke_demo


FULL_REQUIRED = (
    project_root() / "artifacts" / "metrics" / "metrics.json",
    project_root() / "artifacts" / "recommendations" / "top10_recommendations.csv",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _year(title: str) -> int:
    match = re.search(r"\((\d{4})\)\s*$", title)
    return int(match.group(1)) if match else 0


def _movie_catalog() -> dict[int, dict[str, Any]]:
    config = load_config(str(project_root() / "configs" / "full.yaml"))
    path = resolve_input_dir(config) / "movies.csv"
    if not path.is_file():
        return {}
    catalog = {}
    for row in _read_csv(path):
        movie_id = int(row["movieId"])
        catalog[movie_id] = {
            "movieId": movie_id,
            "title": row.get("title", f"Movie {movie_id}"),
            "genres": [genre for genre in row.get("genres", "").split("|") if genre and genre != "(no genres listed)"],
            "year": _year(row.get("title", "")),
        }
    return catalog


def _full_available() -> bool:
    return all(path.is_file() for path in FULL_REQUIRED)


def _normalise_metrics(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    models = metrics.get("models", metrics.get("metrics", {}))
    if not isinstance(models, dict):
        return {}
    return {str(name): dict(values or {}) for name, values in models.items() if isinstance(values, dict)}


def _full_payload() -> dict[str, Any]:
    """Read the outputs of a full run without mixing them with smoke metrics."""
    metrics_path, recommendations_path = FULL_REQUIRED
    metrics = _read_json(metrics_path)
    catalog = _movie_catalog()
    rows = _read_csv(recommendations_path)
    recommendations: list[dict[str, Any]] = []
    by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        user_id = int(row["userId"])
        movie_id = int(row["movieId"])
        movie = catalog.get(movie_id, {"movieId": movie_id, "title": f"Movie {movie_id}", "genres": [], "year": 0})
        item = {
            "userId": user_id,
            "movieId": movie_id,
            "title": movie["title"],
            "genres": movie["genres"],
            "year": movie["year"],
            "rank": int(row.get("rank") or 0),
            "als_score": _float_or_none(row.get("als_score")),
            "rerank_score": _float_or_none(row.get("rerank_score")),
            "model": "hybrid",
            "reasons": ["Chưa có tệp đặc trưng để giải thích gợi ý"],
        }
        recommendations.append(item)
        by_user[user_id].append(item)

    profiles = _load_user_profiles()
    user_ids = sorted(by_user)
    for user_id in user_ids:
        profiles.setdefault(user_id, {
            "userId": user_id,
            "rating_count": None,
            "mean_rating": None,
            "activity_span_days": None,
            "is_long_term": True,
            "train_rows": None,
            "validation_rows": None,
            "test_rows": None,
            "history": None,
        })
    for profile in profiles.values():
        if not isinstance(profile.get("history"), list):
            profile["history"] = None
    checks = _load_json_or_default(project_root() / "artifacts" / "metrics" / "data_quality.json", {})
    pipeline = _load_json_or_default(project_root() / "artifacts" / "metrics" / "pipeline_status.json", {})
    model_metrics = _normalise_metrics(metrics)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": "full",
        "source": "full_artifacts",
        "is_full": True,
        "disclaimer": "Chỉ số đánh giá ngoại tuyến trên MovieLens 25M; không đo trực tiếp sự hài lòng hay tỷ lệ duy trì thuê bao của Netflix.",
        "runtime": "Kết quả từ pipeline full",
        "models": ["popularity", "als", "hybrid"],
        "available_models": ["hybrid"] if recommendations else [],
        "metrics": model_metrics,
        "satisfaction_lift_vs_popularity": metrics.get("satisfaction_lift_vs_popularity"),
        "checks": {
            "leakage_free": checks.get("leakage_free", None),
            "top10_unique": checks.get("top10_unique", None),
            "long_term_users": len(profiles),
            "train_rows": checks.get("train_rows"),
            "validation_rows": checks.get("validation_rows"),
            "test_rows": checks.get("test_rows"),
        },
        "pipeline": _pipeline_rows(pipeline, profile="full"),
        "long_term_users": list(profiles.values()),
        "user_profiles": {str(key): value for key, value in profiles.items()},
        "recommendations": recommendations,
        "recommendations_by_model": {"hybrid": recommendations, "als": [], "popularity": []},
        "movies": list(catalog.values()),
        "data_quality": checks,
        "partial_full_warning": None,
    }


def _load_user_profiles() -> dict[int, dict[str, Any]]:
    candidates = (
        project_root() / "artifacts" / "metrics" / "user_profiles.json",
        project_root() / "artifacts" / "recommendations" / "user_profiles.json",
    )
    for path in candidates:
        if path.is_file():
            raw = _read_json(path)
            values = raw.get("users", raw) if isinstance(raw, dict) else raw
            if isinstance(values, list):
                return {int(row["userId"]): row for row in values}
            if isinstance(values, dict):
                return {int(key): value for key, value in values.items()}
    return {}


def _load_json_or_default(path: Path, default: Any) -> Any:
    return _read_json(path) if path.is_file() else default


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", "null", "None"):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _pipeline_rows(status: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    names = ["RAW", "BRONZE", "SILVER", "GOLD", "ALS", "RE-RANKER", "EVALUATION"]
    rows = []
    for name in names:
        current = status.get(name.lower().replace("-", "_"), {}) if isinstance(status, dict) else {}
        rows.append({
            "name": name,
            "status": current.get("status", "done" if profile == "full" else "unknown"),
            "row_count": current.get("row_count"),
            "path": current.get("path"),
            "duration_seconds": current.get("duration_seconds"),
            "error": current.get("error"),
        })
    return rows


def _normalise_smoke(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload.update({
        "profile": "smoke",
        "source": "fixture",
        "is_full": False,
        "available_models": ["popularity", "als", "hybrid"],
        "partial_full_warning": "Chưa có đủ kết quả full; dashboard đang hiển thị dữ liệu mẫu.",
    })
    payload.setdefault("recommendations_by_model", {"hybrid": payload.get("recommendations", []), "als": [], "popularity": []})
    payload.setdefault("user_profiles", {str(row["userId"]): row for row in payload.get("long_term_users", [])})
    payload.setdefault("data_quality", {})
    return payload


def get_payload() -> dict[str, Any]:
    """Return full results when both required files exist; otherwise run smoke."""
    if _full_available():
        return _full_payload()
    return _normalise_smoke(run_smoke_demo())


def get_users(payload: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    users = list(payload.get("long_term_users", []))
    if query:
        users = [user for user in users if query.lower() in str(user.get("userId", "")).lower()]
    return sorted(users, key=lambda row: int(row.get("userId", 0)))


def get_user(payload: dict[str, Any], user_id: int) -> dict[str, Any] | None:
    profiles = payload.get("user_profiles", {})
    return profiles.get(str(user_id)) or profiles.get(user_id)


def get_recommendations(payload: dict[str, Any], user_id: int, model: str, limit: int = 10) -> list[dict[str, Any]]:
    model = model if model in {"popularity", "als", "hybrid"} else "hybrid"
    rows = payload.get("recommendations_by_model", {}).get(model, [])
    if not rows and model == "hybrid":
        rows = payload.get("recommendations", [])
    return [row for row in rows if int(row.get("userId", -1)) == int(user_id)][: max(1, min(limit, 100))]


def search_movies(payload: dict[str, Any], query: str = "", genre: str = "", year_from: int | None = None, year_to: int | None = None) -> list[dict[str, Any]]:
    rows = payload.get("movies", [])
    query_lower = query.lower().strip()
    genre_lower = genre.lower().strip()
    result = []
    for row in rows:
        title = str(row.get("title", ""))
        genres = row.get("genres", []) or []
        year = int(row.get("year") or 0)
        if query_lower and query_lower not in title.lower():
            continue
        if genre_lower and not any(genre_lower in str(value).lower() for value in genres):
            continue
        if year_from is not None and year and year < year_from:
            continue
        if year_to is not None and year and year > year_to:
            continue
        result.append(row)
    return result[:100]
