from pathlib import Path

from scripts.evaluate_dspy import summarize


def test_summarize_parses_log(tmp_path):
    log = tmp_path / "propose.jsonl"
    log.write_text(
        '{"stage_a":{"ledger":{"tokens_used":10}},"selection":{"ledger":{"tokens_used":20},"selected":[{"id":"1"}]}}\n',
        encoding="utf-8"
    )
    stats = summarize(log)
    assert stats["entries"] == 1
    assert stats["avg_stage_b_tokens"] == 20
