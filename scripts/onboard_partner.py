#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_TRANSPORTS = {
    "defaults": {
        "openai": {"model": "gpt-4o-mini", "timeout": 10, "max_retries": 2},
        "anthropic": {"model": "claude-3-5-sonnet-latest", "timeout": 10, "max_retries": 2},
        "gemini": {"model": "models/gemini-1.5-flash", "timeout": 10, "max_retries": 2},
    },
    "tenants": {},
}

DEFAULT_PILOT = {"defaults": {"allow": False}, "tenants": {}}


def load_config(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return json.loads(json.dumps(default))


def save_config(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_transport_entry(
    transports: Dict[str, Any],
    tenant: str,
    project: str,
    provider: str,
    api_key: str,
    rate_limit: int,
) -> None:
    tenants = transports.setdefault("tenants", {})
    tenant_cfg = tenants.setdefault(tenant, {})
    tenant_cfg.setdefault("projects", {})
    tenant_cfg[provider] = {
        "api_key": api_key,
        "rate_limit_per_min": rate_limit,
        **transports.get("defaults", {}).get(provider, {}),
    }
    project_cfg = tenant_cfg["projects"].setdefault(project, {})
    project_cfg.setdefault(provider, {})


def ensure_pilot_entry(pilot: Dict[str, Any], tenant: str, project: str) -> None:
    tenants = pilot.setdefault("tenants", {})
    tenant_cfg = tenants.setdefault(tenant, {"allow": True})
    tenant_cfg.setdefault("allow", True)
    tenant_cfg.setdefault("projects", {})
    tenant_cfg["projects"][project] = {"allow": True}


def configure_partner(
    *,
    config_dir: Path,
    tenant: str,
    project: str,
    provider_keys: Dict[str, str],
    provider_rates: Dict[str, int],
    skip_pilot: bool = False,
) -> Dict[str, Path]:
    config_dir.mkdir(parents=True, exist_ok=True)
    transports_path = config_dir / "transports.json"
    pilot_path = config_dir / "pilot_cohorts.json"

    transports = load_config(transports_path, DEFAULT_TRANSPORTS)
    pilot = load_config(pilot_path, DEFAULT_PILOT)

    updated_any = False
    for provider, key in provider_keys.items():
        if not key:
            continue
        updated_any = True
        ensure_transport_entry(
            transports,
            tenant=tenant,
            project=project,
            provider=provider,
            api_key=key,
            rate_limit=provider_rates[provider],
        )
    if not updated_any:
        raise ValueError("Provide at least one provider API key (openai, anthropic, gemini).")

    save_config(transports_path, transports)

    if not skip_pilot:
        ensure_pilot_entry(pilot, tenant=tenant, project=project)
        save_config(pilot_path, pilot)

    return {"transports": transports_path, "pilot": pilot_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap pilot transport + cohort configuration")
    parser.add_argument("--config-dir", default="config", help="Directory containing transports.json and pilot_cohorts.json")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--project", default="pilot")
    parser.add_argument("--openai-key")
    parser.add_argument("--anthropic-key")
    parser.add_argument("--gemini-key")
    parser.add_argument("--openai-rate", type=int, default=60)
    parser.add_argument("--anthropic-rate", type=int, default=60)
    parser.add_argument("--gemini-rate", type=int, default=60)
    parser.add_argument("--skip-pilot", action="store_true", help="Skip updating pilot_cohorts.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    provider_keys = {
        "openai": args.openai_key,
        "anthropic": args.anthropic_key,
        "gemini": args.gemini_key,
    }
    provider_rates = {
        "openai": args.openai_rate,
        "anthropic": args.anthropic_rate,
        "gemini": args.gemini_rate,
    }
    paths = configure_partner(
        config_dir=Path(args.config_dir),
        tenant=args.tenant,
        project=args.project,
        provider_keys=provider_keys,
        provider_rates=provider_rates,
        skip_pilot=args.skip_pilot,
    )
    print("Updated:", paths["transports"])
    if not args.skip_pilot:
        print("Updated:", paths["pilot"])


if __name__ == "__main__":
    main()
