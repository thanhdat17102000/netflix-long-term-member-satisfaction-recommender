from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pyspark.sql import types as T

from src.common.config import REQUIRED_RAW_FILES, artifacts_dir, lake_path, load_config
from src.common.spark import create_spark

MANIFEST_SCHEMA = T.StructType(
    [
        T.StructField("filename", T.StringType(), False),
        T.StructField("bytes", T.LongType(), True),
        T.StructField("sha256", T.StringType(), True),
        T.StructField("row_count", T.LongType(), True),
        T.StructField("header", T.StringType(), True),
        T.StructField("checked_at", T.StringType(), True),
        T.StructField("path", T.StringType(), True),
    ]
)


def _sha256_and_bytes(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _header_and_rows(path: Path) -> tuple[str, int]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline().rstrip("\n\r")
        rows = sum(1 for line in handle if line.strip())
    return header, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    raw = lake_path(config, "raw")
    checked_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []

    local_ready = all((Path(raw) / filename).is_file() for filename in REQUIRED_RAW_FILES)
    if local_ready:
        for filename in REQUIRED_RAW_FILES:
            path = Path(raw) / filename
            sha256, nbytes = _sha256_and_bytes(path)
            header, count = _header_and_rows(path)
            rows.append(
                {
                    "filename": filename,
                    "bytes": nbytes,
                    "sha256": sha256,
                    "row_count": count,
                    "header": header,
                    "checked_at": checked_at,
                    "path": str(path).replace("\\", "/"),
                }
            )
    else:
        spark = create_spark("MovieLens-Raw-Manifest", config)
        try:
            for filename in REQUIRED_RAW_FILES:
                path = f"{raw}/{filename}"
                frame = spark.read.option("header", True).csv(path)
                rows.append(
                    {
                        "filename": filename,
                        "bytes": None,
                        "sha256": None,
                        "row_count": int(frame.count()),
                        "header": ",".join(frame.columns),
                        "checked_at": checked_at,
                        "path": path,
                    }
                )
        finally:
            spark.stop()

    spark = create_spark("MovieLens-Raw-Manifest-Write", config)
    try:
        manifest = spark.createDataFrame(rows, schema=MANIFEST_SCHEMA)
        manifest.write.mode("overwrite").json(lake_path(config, "raw", "manifest"))
    finally:
        spark.stop()

    output = artifacts_dir(config)
    (output / "raw_manifest.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Đã tạo manifest RAW cho {len(rows)} tệp")


if __name__ == "__main__":
    main()
