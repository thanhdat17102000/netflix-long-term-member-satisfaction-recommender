#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "05_train_als"
run_spark_job "${PROJECT_ROOT}/src/spark/train_als.py"
echo "STAGE=05_train_als STATUS=ok EXIT=0"
