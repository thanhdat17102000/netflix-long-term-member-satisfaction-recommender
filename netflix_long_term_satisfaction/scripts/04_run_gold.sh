#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "04_run_gold"
run_spark_job "${PROJECT_ROOT}/src/spark/build_gold.py"
echo "STAGE=04_run_gold STATUS=ok EXIT=0"
