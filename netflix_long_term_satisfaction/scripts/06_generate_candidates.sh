#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "06_generate_candidates"
run_spark_job "${PROJECT_ROOT}/src/spark/generate_candidates.py"
run_spark_job "${PROJECT_ROOT}/src/tensorflow/build_reranker_dataset.py"
echo "STAGE=06_generate_candidates STATUS=ok EXIT=0"
