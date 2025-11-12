#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict


def load_json(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_transports(path: Path) -> None:
    data = load_json(path)
    tenants = data.get("tenants", {})
    if not tenants:
        raise ValueError("transports config has no tenants")
    for tenant, cfg in tenants.items():
        for provider in ("openai", "anthropic", "gemini"):
            entry = cfg.get(provider, {})
            if not entry.get("api_key"):
                raise ValueError(f"tenant '{tenant}' missing api_key for {provider}")
            rate = entry.get("rate_limit_per_min")
            if not isinstance(rate, int) or rate <= 0:
                raise ValueError(f"tenant '{tenant}' has invalid rate_limit_per_min for {provider}")


def check_pilot(path: Path) -> None:
    data = load_json(path)
    tenants = data.get("tenants", {})
    if not tenants:
        raise ValueError("pilot config has no tenants defined")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pilot transport configs")
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args()
    base = Path(args.config_dir)
    transport_path = base / "transports.json"
    pilot_path = base / "pilot_cohorts.json"
    check_transports(transport_path)
    check_pilot(pilot_path)
    print("Config validation passed.")


if __name__ == "__main__":
    main()
