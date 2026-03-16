#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Defaults
# -----------------------------
ADR_CUTOFF_DEFAULT=3
RUN_MODES="0,1"

# -----------------------------
# Fixed Paths
# -----------------------------
DELETE_DIR="/home/parthgandhi/data/tmp"
LOG_DIR="/home/parthgandhi/data/logs"

# -----------------------------
# Parse flags
# -----------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --run_modes)
      RUN_MODES="$2"
      shift 2
      ;;
    --end_date)
      END_DATE="$2"
      shift 2
      ;;
    --adr_cutoff)
      ADR_CUTOFF="$2"
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
: "${END_DATE:?--end_date is required}"

ADR_CUTOFF="${ADR_CUTOFF:-$ADR_CUTOFF_DEFAULT}"

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
LOG_FILE="${LOG_DIR}/run_pipeline_${END_DATE}.log"

# -----------------------------
# Activate ENV
# -----------------------------
source .venv/bin/activate

# send stdout + stderr to log
exec > >(tee "${LOG_FILE}") 2>&1

echo "========================================"
echo "Running SwingBot Pipeline"
echo "RUN_MODES=${RUN_MODES}"
echo "END_DATE=${END_DATE}"
echo "ADR_CUTOFF=${ADR_CUTOFF}"
echo "LOG_FILE=${LOG_FILE}"
echo "========================================"

# -----------------------------
# Convert run modes
# -----------------------------
IFS=',' read -ra MODES <<< "$RUN_MODES"

# -----------------------------
# RUN JOBS
# -----------------------------
for MODE in "${MODES[@]}"; do

  # -------------------------
  # MODE 0 : INGESTION
  # -------------------------
  if [[ "$MODE" == "0" ]]; then

    echo "----------------------------------------"
    echo "$(date) Running Ingestion Job"
    echo "----------------------------------------"

    if [[ -d "$DELETE_DIR" ]]; then
        echo "Deleting directory: $DELETE_DIR"
        rm -rf "$DELETE_DIR"
    fi

    CMD="python src/ingest_ohlcv_job.py --end_date ${END_DATE}"

    echo "$CMD"
    eval $CMD
  fi

  # -------------------------
  # MODE 1 : COMPUTE
  # -------------------------
  if [[ "$MODE" == "1" ]]; then

    echo "----------------------------------------"
    echo "$(date) Running Market DB Compute Job"
    echo "----------------------------------------"

    CMD="python src/compute_mkt_db_job.py \
        --end_date ${END_DATE} \
        --adr_cutoff ${ADR_CUTOFF}"

    echo "$CMD"
    eval $CMD
  fi

done

echo "========================================"
echo "$(date) Pipeline Completed Successfully"
echo "========================================"