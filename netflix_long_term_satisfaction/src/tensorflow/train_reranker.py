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
    spark = create_spark("MovieLens-Train-Reranker", config)
    frame = spark.read.parquet(f"{lake_path(config, 'gold')}/reranker_features")
    drop_cols = {
        "userId",
        "movieId",
        "label",
        "title",
        "genres",
        "event_ts",
        "event_date",
        "timestamp",
        "row_number",
        "user_count",
        "train_end",
        "validation_end",
    }
    numeric_types = {"int", "bigint", "smallint", "tinyint", "double", "float", "long"}
    numeric_cols = [
        field.name
        for field in frame.schema.fields
        if field.name not in drop_cols and field.dataType.simpleString() in numeric_types
    ]
    if not numeric_cols:
        spark.stop()
        raise SystemExit("Không tìm thấy cột đặc trưng dạng số cho bộ xếp hạng lại.")
    limited = frame.select(*numeric_cols, "label").limit(int(config["reranker_max_rows"]))
    pdf = limited.toPandas()
    spark.stop()

    labels = pdf.pop("label").astype("float32").to_numpy()
    values = pdf.replace([np.inf, -np.inf], 0).fillna(0).astype("float32").to_numpy()
    if len(values) < 2:
        raise SystemExit("Chưa đủ dữ liệu để huấn luyện bộ xếp hạng lại. Hãy tạo phim ứng viên trước.")

    rng = np.random.default_rng(int(config["seed"]))
    order = rng.permutation(len(values))
    values = values[order]
    labels = labels[order]
    split = max(1, min(len(values) - 1, int(len(values) * 0.8)))
    x_train, x_val = values[:split], values[split:]
    y_train, y_val = labels[:split], labels[split:]

    tf.keras.utils.set_random_seed(int(config["seed"]))
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(values.shape[1],)),
            tf.keras.layers.Dense(256, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=[tf.keras.metrics.AUC(name="auc")])
    history = model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=int(config["reranker_epochs"]),
        batch_size=int(config["reranker_batch_size"]),
        callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=2, restore_best_weights=True)],
        verbose=2,
    )

    output = artifacts_dir(config, "models", "reranker")
    model.save(output / "reranker.keras")
    (output / "feature_columns.json").write_text(json.dumps(numeric_cols, indent=2), encoding="utf-8")
    (output / "history.json").write_text(json.dumps(history.history, indent=2), encoding="utf-8")
    print(f"Đã lưu bộ xếp hạng lại tại {output / 'reranker.keras'}")


if __name__ == "__main__":
    main()
