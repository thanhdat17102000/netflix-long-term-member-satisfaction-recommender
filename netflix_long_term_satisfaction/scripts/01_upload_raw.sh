#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "01_upload_raw"

require_python_package yaml "Install PyYAML: pip install PyYAML>=6.0"

STORAGE="$(config_value storage_backend)"
STORAGE="${STORAGE:-hdfs}"
INPUT_DIR="${PROJECT_ROOT}/$(config_value local_input_dir)"
if [[ "$PROFILE" == "full" && ! -d "$INPUT_DIR" && -f "${PROJECT_ROOT}/data/input/ml-25m.zip" ]]; then
  mkdir -p "$INPUT_DIR"
  unzip -o "${PROJECT_ROOT}/data/input/ml-25m.zip" -d "${PROJECT_ROOT}/data/input" >/dev/null
fi

required=(ratings.csv movies.csv tags.csv links.csv genome-scores.csv genome-tags.csv)
for file in "${required[@]}"; do
  [[ -f "${INPUT_DIR}/${file}" ]] || { echo "Không tìm thấy ${INPUT_DIR}/${file}" >&2; exit 1; }
done

mkdir -p "${PROJECT_ROOT}/artifacts"
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$INPUT_DIR" && sha256sum "${required[@]}" > "${PROJECT_ROOT}/artifacts/raw_manifest.sha256")
else
  "$PYTHON_BIN" - "$INPUT_DIR" "${PROJECT_ROOT}/artifacts/raw_manifest.sha256" <<'PY'
import hashlib, sys
from pathlib import Path
src, dest = Path(sys.argv[1]), Path(sys.argv[2])
lines = []
for name in ["ratings.csv", "movies.csv", "tags.csv", "links.csv", "genome-scores.csv", "genome-tags.csv"]:
    digest = hashlib.sha256((src / name).read_bytes()).hexdigest()
    lines.append(f"{digest}  {name}")
dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
fi

if [[ "$STORAGE" == "local" ]]; then
  WAREHOUSE="${PROJECT_ROOT}/$(config_value local_warehouse)"
  RAW="${WAREHOUSE}/raw"
  mkdir -p "$RAW" "${WAREHOUSE}/bronze" "${WAREHOUSE}/silver" "${WAREHOUSE}/gold" "${WAREHOUSE}/quarantine"
  for file in "${required[@]}"; do
    cp -f "${INPUT_DIR}/${file}" "${RAW}/${file}"
  done
  cp -f "${PROJECT_ROOT}/artifacts/raw_manifest.sha256" "${RAW}/raw_manifest.sha256"
  echo "Dữ liệu RAW cục bộ đã sẵn sàng tại ${RAW}"
  ls -la "$RAW"
else
  if ! command -v hdfs >/dev/null 2>&1; then
    fail_missing "hdfs" "Hadoop 3.3.6 HDFS client is required for storage_backend=hdfs."
  fi
  HDFS_ROOT="$(config_value hdfs_root)"
  HDFS_ROOT="${HDFS_ROOT:-/ml25m}"
  hdfs dfs -mkdir -p "${HDFS_ROOT}/raw" "${HDFS_ROOT}/bronze" "${HDFS_ROOT}/silver" "${HDFS_ROOT}/gold" "${HDFS_ROOT}/quarantine"
  for file in "${required[@]}"; do
    hdfs dfs -put -f "${INPUT_DIR}/${file}" "${HDFS_ROOT}/raw/${file}"
  done
  hdfs dfs -put -f "${PROJECT_ROOT}/artifacts/raw_manifest.sha256" "${HDFS_ROOT}/raw/raw_manifest.sha256"
  hdfs dfs -ls "${HDFS_ROOT}/raw"
fi

run_spark_job "${PROJECT_ROOT}/src/spark/ingest_raw.py"
echo "STAGE=01_upload_raw STATUS=ok EXIT=0"
