from gyre.governance import PolicyEngine, PolicyPack, redact


def test_policy_engine_rejects_large_patch():
    engine = PolicyEngine(PolicyPack(max_tokens=100))
    patch = {"budget": {"tokens_used": 200}}
    res = engine.evaluate(patch, {"tenant": "t", "project": "p", "user": "u"})
    assert not res["allowed"]


def test_redact_masks_sensitive_keys():
    draft = {"content": {"email": "user@example.com"}}
    redacted = redact(draft, {})
    assert redacted["content"]["email"] == "***"
