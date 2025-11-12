#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def load_json(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing config file: {path}. Run `python scripts/onboard_partner.py --tenant demo --project pilot --openai-key ...` first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def check_transports(path: Path) -> None:
    data = load_json(path)
    tenants = data.get("tenants", {})
    errors: list[str] = []
    if not tenants:
        errors.append("transports config has no tenants")
    for tenant, cfg in tenants.items():
        for provider in ("openai", "anthropic", "gemini"):
            entry = cfg.get(provider, {})
            if not entry.get("api_key"):
                errors.append(
                    f"tenant '{tenant}' missing api_key for {provider}. Re-run scripts/onboard_partner.py or edit transports.json."
                )
            rate = entry.get("rate_limit_per_min") or entry.get("max_requests_per_min")
            try:
                rate_val = int(rate)
            except (TypeError, ValueError):
                rate_val = 0
            if rate_val <= 0:
                errors.append(
                    f"tenant '{tenant}' has invalid rate_limit_per_min for {provider}; set a positive integer."
                )
    if errors:
        raise ValueError("\n".join(errors))


def check_pilot(path: Path, tenant_hint: str | None = None, project_hint: str | None = None) -> None:
    data = load_json(path)
    tenants = data.get("tenants", {})
    errors: list[str] = []
    if not tenants:
        errors.append("pilot config has no tenants defined")
    if tenant_hint and project_hint:
        tenant_cfg = tenants.get(tenant_hint)
        if not tenant_cfg:
            errors.append(f"tenant '{tenant_hint}' not found in pilot_cohorts.json")
        else:
            project_cfg = tenant_cfg.get("projects", {}).get(project_hint)
            if not project_cfg or not project_cfg.get("allow"):
                errors.append(
                    f"project '{project_hint}' for tenant '{tenant_hint}' is not enabled. Update pilot_cohorts.json."
                )
    if errors:
        raise ValueError("\n".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pilot transport configs")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--tenant", help="Optional tenant to verify pilot allow list")
    parser.add_argument("--project", help="Optional project to verify pilot allow list")
    args = parser.parse_args()
    base = Path(args.config_dir)
    transport_path = base / "transports.json"
    pilot_path = base / "pilot_cohorts.json"
    check_transports(transport_path)
    check_pilot(pilot_path, tenant_hint=args.tenant, project_hint=args.project)
    print("Config validation passed.")


if __name__ == "__main__":
    main()
