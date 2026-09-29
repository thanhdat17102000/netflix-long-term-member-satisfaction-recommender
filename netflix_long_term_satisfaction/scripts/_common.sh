#!/usr/bin/env bash
# Shared helpers for pipeline scripts. Source this file; do not execute it.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PROJECT_ROOT="${PROJECT_ROOT:-$ROOT}"
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:$PYTHONPATH}"

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Cần Python 3.10 trở lên." >&2
  exit 1
fi

PROFILE="${PROFILE:-full}"
CONFIG_OVERRIDE=""

parse_profile_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile)
        PROFILE="${2:?--profile requires smoke or full}"
        shift 2
        ;;
      --profile=*)
        PROFILE="${1#*=}"
        shift
        ;;
      --config)
        CONFIG_OVERRIDE="${2:?--config requires a yaml path}"
        shift 2
        ;;
      smoke|full)
        PROFILE="$1"
        shift
        ;;
      *)
        echo "Không nhận ra đối số: $1" >&2
        echo "Cách dùng: $0 [--profile smoke|full]" >&2
        exit 2
        ;;
    esac
  done
  if [[ "$PROFILE" != "smoke" && "$PROFILE" != "full" ]]; then
    echo "Cấu hình chạy không hợp lệ: $PROFILE" >&2
    exit 2
  fi
  if [[ -n "$CONFIG_OVERRIDE" ]]; then
    CONFIG="$CONFIG_OVERRIDE"
  else
    CONFIG="${PROJECT_ROOT}/configs/${PROFILE}.yaml"
  fi
  if [[ ! -f "$CONFIG" ]]; then
    echo "Không tìm thấy tệp cấu hình: $CONFIG" >&2
    exit 1
  fi
}

log_stage() {
  local stage="$1"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] STAGE=${stage} PROFILE=${PROFILE} CONFIG=${CONFIG}"
}

fail_missing() {
  echo "Thiếu phần mềm cần thiết: $1" >&2
  echo "$2" >&2
  exit 1
}

config_value() {
  local key="$1"
  "$PYTHON_BIN" - "$CONFIG" "$key" <<'PY'
import sys
import yaml
config = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
print(config.get(sys.argv[2], ""))
PY
}

require_python_package() {
  local module="$1"
  local hint="$2"
  if ! "$PYTHON_BIN" -c "import ${module}" >/dev/null 2>&1; then
    fail_missing "$module" "$hint"
  fi
}

run_python_job() {
  local script="$1"
  shift
  log_stage "$(basename "$script")"
  "$PYTHON_BIN" "$script" --config "$CONFIG" "$@"
}

run_spark_job() {
  local script="$1"
  shift
  require_python_package pyspark "Install Spark 3.5.1 and/or: pip install pyspark==3.5.1"
  log_stage "$(basename "$script")"
  local driver_mem max_result
  driver_mem="$(config_value spark_driver_memory)"
  driver_mem="${driver_mem:-2g}"
  max_result="$(config_value spark_driver_max_result_size)"
  max_result="${max_result:-1g}"
  if command -v spark-submit >/dev/null 2>&1; then
    spark-submit --master local[*] \
      --driver-memory "$driver_mem" \
      --conf "spark.driver.maxResultSize=${max_result}" \
      "$script" --config "$CONFIG" "$@"
  else
    echo "Không tìm thấy spark-submit; thử dùng PySpark qua ${PYTHON_BIN}"
    PYSPARK_SUBMIT_ARGS="--master local[*] --driver-memory ${driver_mem} --conf spark.driver.maxResultSize=${max_result} pyspark-shell" \
      "$PYTHON_BIN" "$script" --config "$CONFIG" "$@"
  fi
}
