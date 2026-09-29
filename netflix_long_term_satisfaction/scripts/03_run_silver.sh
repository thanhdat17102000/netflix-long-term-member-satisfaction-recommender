#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "03_run_silver"
run_spark_job "${PROJECT_ROOT}/src/spark/build_silver.py"
echo "STAGE=03_run_silver STATUS=ok EXIT=0"
