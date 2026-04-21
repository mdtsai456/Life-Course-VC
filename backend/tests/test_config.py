from app.config import get_clone_rate_limit, get_health_rate_limit


def test_empty_clone_rate_limit_uses_default(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_CLONE", "   ")
    assert get_clone_rate_limit() == "10/minute"


def test_empty_health_rate_limit_uses_default(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_HEALTH", "")
    assert get_health_rate_limit() == "60/minute"
