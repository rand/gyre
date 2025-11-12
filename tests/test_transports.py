from gyre.transports import broker
from gyre.transports.config import TransportConfig


class DummyTransport(broker.BaseTransport):
    def __init__(self):
        super().__init__("dummy")
        self.count = 0

    def send(self, patch, *, credentials=None):
        self.ensure_available()
        self.count += 1
        return {"ok": True, "count": self.count}


def test_transport_rate_limit_enforced():
    cfg = TransportConfig(
        data={
            "tenants": {
                "demo": {
                    "dummy": {"rate_limit_per_min": 1},
                }
            }
        }
    )
    dummy = DummyTransport()
    tb = broker.TransportBroker({"dummy": dummy}, transport_config=cfg)
    patch = {"target_session_id": "sess", "body": {"slots": []}}
    tb.inject(patch, scope={"tenant": "demo"})
    try:
        tb.inject(patch, scope={"tenant": "demo"})
    except RuntimeError as exc:
        assert "rate limit exceeded" in str(exc)
    else:
        assert False, "expected rate limit error"
