from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.config import artifacts_dir, lake_path, load_config
from src.common.spark import create_spark


def _require_tensorflow():
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("Cần TensorFlow CPU 2.15.1. Cài bằng: pip install tensorflow-cpu==2.15.1") from exc
    return tf


def main() -> None:
    tf = _require_tensorflow()
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    model_dir = artifacts_dir(config, "models", "reranker")
    columns_path = model_dir / "feature_columns.json"
    model_path = model_dir / "reranker.keras"
    if not columns_path.is_file() or not model_path.is_file():
        raise SystemExit("Chưa có tệp mô hình xếp hạng lại. Hãy huấn luyện mô hình trước khi dự đoán.")

    spark = create_spark("MovieLens-Reranked-Recommendations", config)
    gold = lake_path(config, "gold")
    features = spark.read.parquet(f"{gold}/reranker_test_features")
    feature_columns = json.loads(columns_path.read_text(encoding="utf-8"))
    missing = [column for column in feature_columns if column not in features.columns]
    if missing:
        spark.stop()
        raise SystemExit(f"Tập test thiếu các cột đặc trưng: {missing}")

    model = tf.keras.models.load_model(model_path)
    frame = features.select("userId", "movieId", *feature_columns).limit(int(config["reranker_max_rows"])).toPandas()
    spark.stop()
    if frame.empty:
        raise SystemExit("Chưa có đặc trưng của tập test cho bộ xếp hạng lại.")

    values = frame[feature_columns].replace([np.inf, -np.inf], 0).fillna(0).astype("float32").to_numpy()
    frame["rerank_score"] = model.predict(values, batch_size=int(config["reranker_batch_size"]), verbose=0).reshape(-1)
    ranked = (
        frame.sort_values(["userId", "rerank_score", "movieId"], ascending=[True, False, True])
        .drop_duplicates(["userId", "movieId"])
        .groupby("userId", sort=True, group_keys=False)
        .head(10)
        .copy()
    )
    ranked["rank"] = ranked.groupby("userId").cumcount() + 1
    result = ranked[["userId", "movieId", "rank", "rerank_score"]]

    rec_dir = artifacts_dir(config, "recommendations")
    csv_path = rec_dir / "top10_recommendations.csv"
    result.sort_values(["userId", "rank"]).to_csv(csv_path, index=False)

    spark = create_spark("MovieLens-Reranked-Recommendations-Write", config)
    try:
        spark.createDataFrame(result).write.mode("overwrite").parquet(f"{gold}/reranked_recommendations")
    finally:
        spark.stop()

    user_count = int(result["userId"].nunique())
    print(f"Đã lưu danh sách Top-10 cho {user_count} người dùng tại {csv_path}")
    if user_count < 5:
        print(f"Lưu ý: dữ liệu hiện chỉ có {user_count} người dùng đủ điều kiện; mục tiêu là ít nhất 5 khi dữ liệu cho phép.")


if __name__ == "__main__":
    main()
