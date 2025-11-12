from pathlib import Path

from typer.testing import CliRunner

from scripts import gyre_cli


runner = CliRunner()


class DummyResponse:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


def test_register_session_cli(monkeypatch):
    def fake_request(method, url, json=None, timeout=10):
        assert method == "POST"
        assert url.endswith("/sessions/register")
        return DummyResponse({"session_id": json["session_id"], "scope": json})

    monkeypatch.setattr("httpx.request", fake_request)
    result = runner.invoke(gyre_cli.app, ["register-session", "sess-1", "tenant", "project", "user"])
    assert result.exit_code == 0


def test_give_consent_cli(monkeypatch):
    seen = {}

    def fake_request(method, url, json=None, timeout=10):
        seen.update(json)
        return DummyResponse({"ok": True})

    monkeypatch.setattr("httpx.request", fake_request)
    result = runner.invoke(gyre_cli.app, ["give-consent", "tenant", "proj", "user", "--no-consent"])
    assert result.exit_code == 0
    assert seen == {"tenant": "tenant", "project": "proj", "user": "user", "consent": False}


def test_learning_cycle_cli(monkeypatch):
    calls = []

    def fake_run(cmd, check):
        calls.append((tuple(cmd), check))
        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = runner.invoke(
        gyre_cli.app,
        ["learning-cycle", "--log", "custom.log", "--data-dir", "custom", "--feedback", "feedback.jsonl"],
    )
    assert result.exit_code == 0
    assert calls[0][0][0] == "bash"


def test_transport_health_cli(monkeypatch):
    def fake_request(method, url, json=None, timeout=10):
        assert method == "GET"
        assert json is None
        return DummyResponse(
            {
                "status": "ok",
                "transports": [
                    {
                        "name": "openai",
                        "available": True,
                        "failures": 0,
                        "cooldown_seconds": 0.0,
                        "metrics": {
                            "scopes": [
                                {"tenant": "demo", "project": "pilot", "success": 2, "failure": 0, "last_latency_ms": 42.0, "last_error": None}
                            ]
                        },
                    }
                ],
            }
        )

    monkeypatch.setattr("httpx.request", fake_request)
    result = runner.invoke(gyre_cli.app, ["transport-health"])
    assert result.exit_code == 0
    assert "Transport health: OK" in result.stdout
    assert "scope demo/pilot" in result.stdout


def test_onboard_partner_cli_validates(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, check=True):
        calls.append(cmd)
        class _Result:
            stderr = ""
        return _Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    validated = {}

    def fake_validate_configs(*, config_dir, tenant=None, project=None):
        validated["config_dir"] = config_dir
        validated["tenant"] = tenant
        validated["project"] = project

    monkeypatch.setattr(gyre_cli, "validate_configs", fake_validate_configs)
    result = runner.invoke(
        gyre_cli.app,
        ["onboard-partner", "--tenant", "acme", "--config-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert calls
    assert validated["tenant"] == "acme"
    assert Path(validated["config_dir"]) == tmp_path


def test_onboard_partner_cli_skips_validate(monkeypatch, tmp_path):
    def fake_run(cmd, check=True):
        class _Result:
            stderr = ""
        return _Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    called = {}

    def fake_validate_configs(**kwargs):
        called["ran"] = True

    monkeypatch.setattr(gyre_cli, "validate_configs", fake_validate_configs)
    result = runner.invoke(
        gyre_cli.app,
        ["onboard-partner", "--tenant", "acme", "--config-dir", str(tmp_path), "--no-validate"],
    )
    assert result.exit_code == 0
    assert "ran" not in called


def test_ingest_missing_trace(monkeypatch, tmp_path):
    missing = tmp_path / "missing.jsonl"

    def fake_request(*args, **kwargs):
        raise AssertionError("request should not be called")

    monkeypatch.setattr(gyre_cli, "request", fake_request)
    result = runner.invoke(gyre_cli.app, ["ingest", "sess-1", str(missing)])
    assert result.exit_code == 1
    assert "File not found" in result.stdout
