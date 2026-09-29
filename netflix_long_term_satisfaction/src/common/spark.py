from __future__ import annotations

from typing import Any

from pyspark.sql import SparkSession

from src.common.config import warehouse_root


def create_spark(app_name: str, config: dict[str, Any]) -> SparkSession:
    builder = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.shuffle.partitions", str(config.get("spark_partitions", 200)))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.ui.showConsoleProgress", "false")
    )
    backend = str(config.get("storage_backend", "hdfs")).lower()
    if backend == "local":
        warehouse = warehouse_root(config)
        builder = (
            builder
            .master(str(config.get("spark_master", "local[*]")))
            .config("spark.sql.warehouse.dir", f"{warehouse}/_spark_warehouse")
            .config("spark.driver.host", "127.0.0.1")
        )
    else:
        namenode = str(config.get("hdfs_namenode", "hdfs://namenode:9000")).rstrip("/")
        builder = (
            builder
            .master(str(config.get("spark_master", "local[*]")))
            .config("spark.hadoop.fs.defaultFS", namenode)
            .config("spark.hadoop.dfs.replication", "1")
            .config("spark.hadoop.dfs.permissions.enabled", "false")
            .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
            .config("spark.driver.memory", str(config.get("spark_driver_memory", "10g")))
            .config("spark.driver.maxResultSize", str(config.get("spark_driver_max_result_size", "4g")))
            .config("spark.driver.host", "127.0.0.1")
        )
    return builder.getOrCreate()
