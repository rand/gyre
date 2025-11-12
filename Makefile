# Minimal make tasks using uv
.PHONY: setup run test seed log compile-dspy eval-dspy

setup:
	uv venv
	uv pip install -e .

run:
	uv run python server/run_dev_server.py

test:
	uv run pytest -q

seed:
	uv run python scripts/seed_datasets.py

log:
	uv run python scripts/log_examples.py --responses data/logs/propose.jsonl --out data/train

compile-dspy:
	DSPY_MOCK=1 uv run python scripts/compile_dspy.py --data-dir data/train

eval-dspy:
	uv run python scripts/evaluate_dspy.py --log data/logs/propose.jsonl
