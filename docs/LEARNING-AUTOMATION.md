# Learning Automation

Run the feedback-aware pipeline nightly to keep DSPy modules current:

## GitHub Actions Sample
```yaml
name: nightly-learning
on:
  schedule:
    - cron: "0 7 * * *"
jobs:
  learning:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/uv-action@v1
      - run: uv sync
      - run: |
          DSPY_NEGATIVE_SAMPLES=3 \
          DSPY_ACCEPTED_WEIGHT=1.0 \
          DSPY_REJECTED_WEIGHT=0.2 \
          LEARNING_REPORT_PATH=dist/learning/metrics.json \
          ./scripts/run_learning_cycle.sh data/logs/propose.jsonl data/train data/feedback.jsonl
      - run: git diff data/train && git status
```

## Cron Example
```
0 2 * * * cd /opt/gyre && ./scripts/run_learning_cycle.sh /var/gyre/logs/propose.jsonl /var/gyre/data/train /var/gyre/data/feedback.jsonl >> /var/log/gyre/learning.log 2>&1
```

Set `LEARNING_REPORT_PATH` to capture the evaluation JSON for dashboards or artifact uploads. The script rebuilds datasets, compiles DSPy, and emits evaluation stats; ship the resulting reports/logs to your observability stack (e.g., push `scripts/evaluate_dspy.py` output into Graphite or `/metrics/dspy`).

> See `.github/workflows/nightly-learning.yml` for the production-ready workflow that runs every morning, captures logs under `dist/learning/`, and uploads datasets + DSPy cache as artifacts.

## Feedback weighting & negative sampling
- `DSPY_ACCEPTED_WEIGHT`, `DSPY_REJECTED_WEIGHT`, and `DSPY_DEFAULT_WEIGHT` (or the corresponding `--accepted-weight`, `--rejected-weight`, `--default-weight` flags on `scripts/build_dspy_datasets.py`) control how much accepted vs. rejected verdicts influence the DSPy ranker training records.
- `DSPY_NEGATIVE_SAMPLES` (or `--negative-samples`) determines how many non-selected candidate IDs are tagged as negatives whenever a host rejection is logged. Sampling is deterministic per candidate ID, so datasets are stable between runs.
- `data/learning_cycle.json` is written at the end of every successful run with `{"timestamp": ..., "last_run_iso": ...}` so the server can export `gyre_learning_last_run_timestamp` via Prometheus. Override the location with `LEARNING_META_PATH` if you run automation outside the repo root, and keep this file in your backups.
