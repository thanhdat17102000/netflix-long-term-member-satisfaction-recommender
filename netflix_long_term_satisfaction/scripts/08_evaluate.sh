#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "08_evaluate"
require_python_package matplotlib "Install matplotlib: pip install matplotlib>=3.7"
run_spark_job "${PROJECT_ROOT}/src/evaluation/evaluate.py"
echo "STAGE=08_evaluate STATUS=ok EXIT=0"
