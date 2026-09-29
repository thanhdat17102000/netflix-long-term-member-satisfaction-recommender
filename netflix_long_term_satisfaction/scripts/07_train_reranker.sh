#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"
parse_profile_args "$@"
log_stage "07_train_reranker"
require_python_package tensorflow "Install TensorFlow CPU 2.15.1: pip install tensorflow-cpu==2.15.1"
run_spark_job "${PROJECT_ROOT}/src/tensorflow/train_reranker.py"
run_spark_job "${PROJECT_ROOT}/src/tensorflow/predict_reranked.py"
echo "STAGE=07_train_reranker STATUS=ok EXIT=0"
