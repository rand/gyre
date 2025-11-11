from gyre.transports.broker import TransportBroker, flatten_blueprint


def test_broker_prefers_available_transport():
    broker = TransportBroker.default()
    patch = {
        "target_session_id": "sess-1",
        "body": {"slots": [{"name": "task_header", "content": "Test"}]},
    }
    result = broker.inject(patch, preferred="openai")
    assert result["transport"] == "openai"


def test_flatten_blueprint():
    text = flatten_blueprint({"slots": [{"name": "constraints", "content": "Stay safe"}]})
    assert "[constraints]" in text
