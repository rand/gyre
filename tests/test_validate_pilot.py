from pathlib import Path

import pytest

from scripts import validate_pilot


def test_check_transports_errors(tmp_path: Path):
    config = tmp_path / "transports.json"
    config.write_text(
        '{"tenants":{"demo":{"openai":{"api_key":"","rate_limit_per_min":0}}}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc:
        validate_pilot.check_transports(config)
    assert "missing api_key" in str(exc.value)


def test_check_pilot_scope(tmp_path: Path):
    pilot = tmp_path / "pilot.json"
    pilot.write_text('{"tenants":{"demo":{"allow":true,"projects":{"pilot":{"allow":true}}}}}', encoding="utf-8")
    # No error when allowed
    validate_pilot.check_pilot(pilot, tenant_hint="demo", project_hint="pilot")
    # Error when missing tenant
    with pytest.raises(ValueError):
        validate_pilot.check_pilot(pilot, tenant_hint="unknown", project_hint="pilot")
