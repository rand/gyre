import json
from pathlib import Path

from scripts import onboard_partner


def test_configure_partner_writes_files(tmp_path: Path):
    paths = onboard_partner.configure_partner(
        config_dir=tmp_path,
        tenant="acme",
        project="pilot",
        provider_keys={"openai": "sk-openai", "anthropic": "", "gemini": ""},
        provider_rates={"openai": 50, "anthropic": 60, "gemini": 60},
        skip_pilot=False,
    )
    transports = json.loads((tmp_path / "transports.json").read_text(encoding="utf-8"))
    assert transports["tenants"]["acme"]["openai"]["api_key"] == "sk-openai"
    pilot = json.loads((tmp_path / "pilot_cohorts.json").read_text(encoding="utf-8"))
    assert pilot["tenants"]["acme"]["projects"]["pilot"]["allow"] is True
    assert paths["transports"].exists()
