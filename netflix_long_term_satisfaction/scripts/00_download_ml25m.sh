#!/usr/bin/env bash
# Download MovieLens 25M into data/input/ml-25m.
# Prefers Kaggle when kaggle.json is present; otherwise uses the official GroupLens zip.
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

INPUT_PARENT="${PROJECT_ROOT}/data/input"
DEST="${INPUT_PARENT}/ml-25m"
ZIP="${INPUT_PARENT}/ml-25m.zip"
GROUP_LENS_URL="https://files.grouplens.org/datasets/movielens/ml-25m.zip"
KAGGLE_SLUG="grouplens/movielens-25m-dataset"
required=(ratings.csv movies.csv tags.csv links.csv genome-scores.csv genome-tags.csv)

files_ready() {
  local name
  for name in "${required[@]}"; do
    [[ -f "${DEST}/${name}" ]] || return 1
  done
}

normalize_layout() {
  if files_ready; then
    return 0
  fi
  local found srcdir name
  found="$(find "$INPUT_PARENT" -type f -name ratings.csv | head -n 1 || true)"
  if [[ -z "$found" ]]; then
    return 1
  fi
  srcdir="$(dirname "$found")"
  mkdir -p "$DEST"
  if [[ "$srcdir" != "$DEST" ]]; then
    for name in "${required[@]}"; do
      [[ -f "${srcdir}/${name}" ]] || return 1
      cp -f "${srcdir}/${name}" "${DEST}/${name}"
    done
  fi
  files_ready
}

find_kaggle_json() {
  local candidate
  for candidate in \
    "${KAGGLE_CONFIG:-}" \
    "${HOME:-}/.kaggle/kaggle.json" \
    "${PROJECT_ROOT}/kaggle.json" \
    "${PROJECT_ROOT}/docker/kaggle.json"
  do
    if [[ -n "$candidate" && -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

download_grouplens() {
  echo "Downloading official GroupLens ml-25m.zip"
  mkdir -p "$INPUT_PARENT"
  if [[ ! -f "$ZIP" ]]; then
    curl -fL --retry 3 --retry-delay 2 -o "$ZIP" "$GROUP_LENS_URL"
  fi
  unzip -o "$ZIP" -d "$INPUT_PARENT" >/dev/null
}

download_kaggle() {
  local kaggle_json="$1"
  export KAGGLE_CONFIG_DIR
  KAGGLE_CONFIG_DIR="$(dirname "$kaggle_json")"
  if ! command -v kaggle >/dev/null 2>&1; then
    "$PYTHON_BIN" -m pip install --quiet kaggle
  fi
  echo "Downloading MovieLens 25M from Kaggle (${KAGGLE_SLUG})"
  mkdir -p "$INPUT_PARENT"
  kaggle datasets download -d "$KAGGLE_SLUG" -p "$INPUT_PARENT" --unzip
}

if files_ready; then
  echo "MovieLens 25M already present: ${DEST}"
  exit 0
fi

mkdir -p "$INPUT_PARENT"
if kaggle_json="$(find_kaggle_json)"; then
  if ! download_kaggle "$kaggle_json"; then
    echo "Kaggle download failed; falling back to GroupLens" >&2
    download_grouplens
  fi
else
  echo "No kaggle.json found; using the GroupLens zip that Kaggle redistributes"
  download_grouplens
fi

if ! normalize_layout; then
  echo "MovieLens 25M is missing one of: ${required[*]}" >&2
  exit 1
fi
echo "MovieLens 25M ready: ${DEST}"
