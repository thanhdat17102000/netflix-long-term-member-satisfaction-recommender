#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "02_run_bronze"
run_spark_job "${PROJECT_ROOT}/src/spark/build_bronze.py"
echo "STAGE=02_run_bronze STATUS=ok EXIT=0"
