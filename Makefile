# Minimal make tasks using uv
.PHONY: setup run test seed

setup:
	uv venv
	uv pip install -e .

run:
	uv run python server/run_dev_server.py

test:
	uv run pytest -q

seed:
	uv run python scripts/seed_datasets.py
