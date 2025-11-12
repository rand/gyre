#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

import httpx
import typer

app = typer.Typer(help="Gyre interactive CLI")
BASE_URL = os.environ.get("GYRE_BASE_URL", "http://localhost:8000")


def _load_jsonl(path: Path) -> list[dict]:
    path = path.expanduser()
    if not path.exists():
        typer.secho(f"File not found: {path}", fg=typer.colors.RED)
        raise typer.Exit(1)
    lines = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                lines.append(json.loads(line))
    except json.JSONDecodeError as exc:
        typer.secho(f"Failed to parse JSON in {path}: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)
    return lines


def _load_json(path: Path) -> Dict[str, Any]:
    path = path.expanduser()
    if not path.exists():
        typer.secho(f"File not found: {path}", fg=typer.colors.RED)
        raise typer.Exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.secho(f"Failed to parse JSON in {path}: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


def _run_subprocess(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        typer.secho(f"Executable not found while running {cmd[0]}: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except subprocess.CalledProcessError as exc:
        typer.secho(exc.stderr or f"Command {' '.join(cmd)} failed with {exc.returncode}", fg=typer.colors.RED)
        raise typer.Exit(exc.returncode)


def request(method: str, path: str, json_body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    url = f"{BASE_URL.rstrip('/')}{path}"
    try:
        kwargs: Dict[str, Any] = {"timeout": 10}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = httpx.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        typer.secho(f"Error {exc.response.status_code}: {detail}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as exc:
        typer.secho(f"Request failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def register_session(session_id: str, tenant: str, project: str, user: str):
    """Register a session scope before ingesting."""
    payload = {"session_id": session_id, "tenant": tenant, "project": project, "user": user}
    resp = request("POST", "/sessions/register", payload)
    typer.secho(f"Registered session {resp['session_id']} with scope {resp['scope']}", fg="green")


@app.command()
def ingest(session_id: str, trace: Path):
    """Ingest a JSON/JSONL trace via /observe/ingest."""
    events = _load_jsonl(trace)
    payload = {"session_id": session_id, "events": events}
    resp = request("POST", "/observe/ingest", payload)
    typer.secho(f"Ingested {len(events)} events. Novelty: {resp['state']['novelty']['score']:.2f}", fg="green")


@app.command()
def propose(session_id: str, task_desc: str, tokens: int = 800, latency_ms: int = 800):
    """Call /patches/propose with default budgets."""
    payload = {
        "session_id": session_id,
        "task_desc": task_desc,
        "budgets": {"tokens": tokens, "latency_ms": latency_ms},
        "slot_specs": [{"name": "task_header", "max_tokens": 200}],
    }
    resp = request("POST", "/patches/propose", payload)
    patch = resp["patches"][0]
    typer.secho(f"Proposed patch {patch['id']} with ledger {resp['ledger']}", fg="green")


@app.command()
def inject(patch_file: Path, transport: str = "best"):
    """Inject a patch JSON using /patches/inject."""
    patch = _load_json(patch_file)
    payload = {"patch": patch, "transport": transport}
    resp = request("POST", "/patches/inject", payload)
    typer.secho(f"Injected via {resp['transport']}: ack={resp['ack']}", fg="green")


@app.command()
def validate_configs(
    config_dir: Path = Path("config"),
    tenant: str = typer.Option(None, help="Optional tenant to verify"),
    project: str = typer.Option(None, help="Optional project to verify"),
):
    """Run scripts/validate_pilot.py with friendly errors."""
    cmd = ["python3", "scripts/validate_pilot.py", "--config-dir", str(config_dir)]
    if tenant:
        cmd.extend(["--tenant", tenant])
    if project:
        cmd.extend(["--project", project])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        typer.secho("python3 not found; install Python 3.10+.", fg="red")
        raise typer.Exit(1)
    if result.returncode != 0:
        typer.secho(result.stderr or result.stdout, fg="red")
        raise typer.Exit(result.returncode)
    typer.secho(result.stdout.strip(), fg="green")


@app.command()
def give_consent(
    tenant: str,
    project: str,
    user: str,
    consent: bool = typer.Option(True, "--consent/--no-consent", help="Toggle consent on/off"),
):
    """Call /governance/consent for a scope."""
    payload = {"tenant": tenant, "project": project, "user": user, "consent": consent}
    request("POST", "/governance/consent", payload)
    typer.secho(f"Consent={consent} recorded for {tenant}/{project}/{user}", fg="green")


@app.command()
def transport_health(raw: bool = typer.Option(False, "--raw", help="Print raw JSON response")):
    """Print /health/transports summary."""
    resp = request("GET", "/health/transports")
    if raw:
        typer.echo(json.dumps(resp, indent=2))
        return
    status = (resp.get("status") or "unknown").upper()
    color = "green" if status == "OK" else ("yellow" if status == "DEGRADED" else "red")
    typer.secho(f"Transport health: {status}", fg=color)
    transports = resp.get("transports") or []
    if not transports:
        typer.echo("No transports configured.")
        return
    for info in transports:
        name = info.get("name", "unknown")
        available = info.get("available", True)
        failures = info.get("failures", 0)
        cooldown = info.get("cooldown_seconds", 0.0)
        state = "UP" if available else "DOWN"
        typer.echo(f"- {name}: {state}, failures={failures}, cooldown={cooldown:.1f}s")
        scopes = (info.get("metrics") or {}).get("scopes") or []
        for scope in scopes:
            tenant = scope.get("tenant") or "tenant"
            project = scope.get("project") or "*"
            success = scope.get("success", 0)
            failure = scope.get("failure", 0)
            typer.echo(f"    scope {tenant}/{project}: {success} ok, {failure} fail")


@app.command()
def onboard_partner(
    tenant: str = typer.Option(..., "--tenant", "-t", help="Tenant identifier"),
    project: str = typer.Option("pilot", "--project", "-p", help="Project identifier"),
    openai_key: str = "",
    anthropic_key: str = "",
    gemini_key: str = "",
    config_dir: Path = Path("config"),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Run validate-configs after onboarding"),
):
    """Wrap scripts/onboard_partner.py."""
    cmd = [
        "python3",
        "scripts/onboard_partner.py",
        "--tenant",
        tenant,
        "--project",
        project,
        "--config-dir",
        str(config_dir),
    ]
    if openai_key:
        cmd.extend(["--openai-key", openai_key])
    if anthropic_key:
        cmd.extend(["--anthropic-key", anthropic_key])
    if gemini_key:
        cmd.extend(["--gemini-key", gemini_key])
    _run_subprocess(cmd)
    typer.secho("Onboarding complete.", fg="green")
    if validate:
        typer.secho("Validating configs...", fg="yellow")
        validate_configs(config_dir=config_dir, tenant=tenant, project=project)


@app.command()
def learning_cycle(
    log: Path = Path("data/logs/propose.jsonl"),
    data_dir: Path = Path("data/train"),
    feedback: Path = Path("data/feedback.jsonl"),
):
    """Run scripts/run_learning_cycle.sh."""
    cmd = ["bash", "scripts/run_learning_cycle.sh", str(log), str(data_dir), str(feedback)]
    _run_subprocess(cmd)


@app.command()
def guide():
    """Interactive flow covering registration → ingest → propose."""
    session_id = typer.prompt("Session ID", default="sess-demo")
    tenant = typer.prompt("Tenant", default="demo")
    project = typer.prompt("Project", default="pilot")
    user = typer.prompt("User", default=session_id)
    register_session(session_id, tenant, project, user)
    trace_file = typer.prompt("Trace file", default="traces/example.jsonl")
    ingest(session_id, Path(trace_file))
    task_desc = typer.prompt("Task description", default="Need pilot status summary")
    propose(session_id, task_desc)
    typer.secho("Guide complete. Use `gyre inject` once you've reviewed the patch.", fg="yellow")


if __name__ == "__main__":
    app()
