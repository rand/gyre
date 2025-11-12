from pathlib import Path

from gyre.logger import DatasetLogger


class Payload:
    def __init__(self):
        self.task_desc = "Test"
        self.session_id = "sess"
        self.budgets = {"tokens": 100}


def test_dataset_logger_writes_json(tmp_path):
    log_path = tmp_path / "logs" / "propose.jsonl"
    logger = DatasetLogger(log_path)
    logger.log_propose(Payload(), {"ledger": {}}, {"ledger":{}}, {"id":"patch"})
    lines = log_path.read_text().strip().splitlines()
    assert lines
