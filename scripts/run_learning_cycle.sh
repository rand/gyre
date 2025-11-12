#!/usr/bin/env bash
set -euo pipefail

LOG_PATH=${1:-data/logs/propose.jsonl}
DATA_DIR=${2:-data/train}
FEEDBACK_PATH=${3:-data/feedback.jsonl}
LEARNING_META_PATH=${LEARNING_META_PATH:-data/learning_cycle.json}
ACCEPTED_WEIGHT=${DSPY_ACCEPTED_WEIGHT:-1.0}
REJECTED_WEIGHT=${DSPY_REJECTED_WEIGHT:-0.25}
DEFAULT_WEIGHT=${DSPY_DEFAULT_WEIGHT:-1.0}
NEGATIVE_SAMPLES=${DSPY_NEGATIVE_SAMPLES:-2}

echo "[learning] building datasets from ${LOG_PATH} -> ${DATA_DIR}"
uv run python scripts/build_dspy_datasets.py \
  --log "$LOG_PATH" \
  --out "$DATA_DIR" \
  --feedback "$FEEDBACK_PATH" \
  --accepted-weight "$ACCEPTED_WEIGHT" \
  --rejected-weight "$REJECTED_WEIGHT" \
  --default-weight "$DEFAULT_WEIGHT" \
  --negative-samples "$NEGATIVE_SAMPLES"

echo "[learning] compiling DSPy programs"
DSPY_MOCK=${DSPY_MOCK:-0} uv run python scripts/compile_dspy.py --data-dir "$DATA_DIR"

echo "[learning] evaluating DSPy logs"
if [[ -n "${LEARNING_REPORT_PATH:-}" ]]; then
  mkdir -p "$(dirname "$LEARNING_REPORT_PATH")"
  uv run python scripts/evaluate_dspy.py --log "$LOG_PATH" | tee "$LEARNING_REPORT_PATH"
else
  uv run python scripts/evaluate_dspy.py --log "$LOG_PATH"
fi

echo "[learning] done"

python3 - <<'PY'
import json
import time
from pathlib import Path
from datetime import datetime, timezone
meta = {
    "last_run_iso": datetime.now(timezone.utc).isoformat(),
    "timestamp": time.time(),
    "log_path": "${LOG_PATH}",
    "data_dir": "${DATA_DIR}"
}
path = Path("${LEARNING_META_PATH}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
PY
