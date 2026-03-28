#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Defaults
# -----------------------------
# (none for now)

# -----------------------------
# Fixed Paths
# -----------------------------
LOG_DIR="/home/parthgandhi/data/logs"

# -----------------------------
# Parse flags
# -----------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fetch_date)
      FETCH_DATE="$2"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

# -----------------------------
# Required args
# -----------------------------
: "${FETCH_DATE:?--fetch_date is required}"

# -----------------------------
# Project root
# -----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

cd "${PROJECT_ROOT}"

# -----------------------------
# Logs
# -----------------------------
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/run_nse_industry_${FETCH_DATE}.log"

# -----------------------------
# Activate ENV
# -----------------------------
source .venv/bin/activate

# send stdout + stderr to log
exec > >(tee "${LOG_FILE}") 2>&1

echo "========================================"
echo "Running NSE Industry Pipeline"
echo "FETCH_DATE=${FETCH_DATE}"
echo "LOG_FILE=${LOG_FILE}"
echo "========================================"

# -----------------------------
# RUN JOB
# -----------------------------
echo "----------------------------------------"
echo "$(date) Running NSE Industry Ingestion"
echo "----------------------------------------"

CMD="python src/ingest_nse_industry_job.py --fetch_date ${FETCH_DATE}"

echo "$CMD"
eval $CMD

echo "========================================"
echo "$(date) NSE Industry Pipeline Completed Successfully"
echo "========================================"