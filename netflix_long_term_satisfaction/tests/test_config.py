from src.common.config import artifacts_dir, lake_path, load_config, resolve_input_dir


def test_load_smoke_and_full_config(project_root):
    smoke = load_config(str(project_root / "configs" / "smoke.yaml"))
    full = load_config(str(project_root / "configs" / "full.yaml"))
    assert smoke["seed"] == 42
    assert full["seed"] == 42
    assert smoke["positive_rating_threshold"] == 4.0
    assert full["positive_rating_threshold"] == 4.0
    assert full["long_term_min_days"] == 180
    assert full["long_term_min_ratings"] == 20
    assert full["als_rank"] == 64
    assert full["als_reg_param"] == 0.1
    assert full["als_max_iter"] == 10
    assert full.get("implicitPrefs", False) is False
    assert smoke["storage_backend"] == "local"
    assert full["storage_backend"] == "hdfs"
    assert full["hdfs_namenode"] == "hdfs://namenode:9000"
    assert full["hdfs_root"] == "/ml25m"
    assert full["spark_driver_memory"] == "10g"
    assert lake_path(full, "raw").replace("\\", "/") == "/ml25m/raw"


def test_smoke_output_paths(project_root):
    config = load_config(str(project_root / "configs" / "smoke.yaml"))
    raw = lake_path(config, "raw").replace("\\", "/")
    bronze = lake_path(config, "bronze").replace("\\", "/")
    silver = lake_path(config, "silver").replace("\\", "/")
    gold_train = lake_path(config, "gold", "train").replace("\\", "/")
    assert raw.endswith("ml25m_smoke/raw")
    assert bronze.endswith("ml25m_smoke/bronze")
    assert silver.endswith("ml25m_smoke/silver")
    assert gold_train.endswith("ml25m_smoke/gold/train")
    assert resolve_input_dir(config).name == "ml-25m"
    metrics_dir = artifacts_dir(config, "metrics")
    assert metrics_dir.name == "metrics"
    assert "artifacts" in str(metrics_dir).replace("\\", "/")
