from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REQUIRED_RAW_FILES = (
    "ratings.csv",
    "movies.csv",
    "tags.csv",
    "links.csv",
    "genome-scores.csv",
    "genome-tags.csv",
)

MOVIELENS_HEADERS = {
    "ratings.csv": ["userId", "movieId", "rating", "timestamp"],
    "movies.csv": ["movieId", "title", "genres"],
    "tags.csv": ["userId", "movieId", "tag", "timestamp"],
    "links.csv": ["movieId", "imdbId", "tmdbId"],
    "genome-scores.csv": ["movieId", "tagId", "relevance"],
    "genome-tags.csv": ["tagId", "tag"],
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: str) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config["_config_path"] = str(config_path)
    config["_project_root"] = str(project_root())
    config.setdefault("storage_backend", "hdfs")
    config.setdefault("local_warehouse", "data/warehouse/ml25m")
    config.setdefault("min_split_interactions", 3)
    config.setdefault("train_ratio", 0.8)
    config.setdefault("validation_ratio", 0.1)
    return config


def warehouse_root(config: dict[str, Any]) -> str:
    backend = str(config.get("storage_backend", "hdfs")).lower()
    if backend == "local":
        raw = config.get("local_warehouse") or "data/warehouse/ml25m"
        path = Path(str(raw))
        if not path.is_absolute():
            path = project_root() / path
        return str(path.resolve()).replace("\\", "/")
    return str(config["hdfs_root"]).rstrip("/")


def lake_path(config: dict[str, Any], *parts: str) -> str:
    root = warehouse_root(config).rstrip("/")
    joined = "/".join([root, *[str(part).strip("/\\") for part in parts]])
    return joined.replace("\\", "/")


def hdfs_path(config: dict[str, Any], *parts: str) -> str:
    return lake_path(config, *parts)


def artifacts_dir(config: dict[str, Any] | None = None, *parts: str) -> Path:
    base = project_root() / "artifacts"
    path = base.joinpath(*parts) if parts else base
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_input_dir(config: dict[str, Any]) -> Path:
    raw = Path(str(config.get("local_input_dir", "data/input/ml-25m")))
    if not raw.is_absolute():
        raw = project_root() / raw
    return raw
