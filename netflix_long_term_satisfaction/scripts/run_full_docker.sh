#!/usr/bin/env bash
# Start single-node HDFS, then run the MovieLens 25M pipeline inside the pipeline container.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f docker/docker-compose.yml)

"${COMPOSE[@]}" up -d --build

echo "Waiting for HDFS to leave safe mode"
ready=0
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T namenode hdfs dfsadmin -safemode get 2>/dev/null | grep -q "Safe mode is OFF"; then
    ready=1
    break
  fi
  sleep 5
done
if [[ "$ready" -ne 1 ]]; then
  echo "NameNode did not leave safe mode" >&2
  "${COMPOSE[@]}" logs namenode datanode
  exit 1
fi

scripts=(
  00_download_ml25m.sh
  01_upload_raw.sh
  02_run_bronze.sh
  03_run_silver.sh
  04_run_gold.sh
  05_train_als.sh
  06_generate_candidates.sh
  07_train_reranker.sh
  08_evaluate.sh
)
for script in "${scripts[@]}"; do
  if [[ "$script" == "00_download_ml25m.sh" ]]; then
    "${COMPOSE[@]}" exec -T pipeline bash "scripts/${script}"
  else
    "${COMPOSE[@]}" exec -T pipeline bash "scripts/${script}" --profile full
  fi
done

echo "Full pipeline finished"
