import sys

import pytest


@pytest.fixture
def health_handlers(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "true")

    for name in list(sys.modules):
        if name.startswith("app."):
            del sys.modules[name]

    from app.core.config import get_settings
    from app.main import healthz, metrics, readyz

    get_settings.cache_clear()

    return healthz, readyz, metrics


def test_healthz_returns_ok(health_handlers):
    healthz, _, _ = health_handlers
    assert healthz() == {"status": "ok"}


def test_readyz_checks_database_connection(health_handlers):
    _, readyz, _ = health_handlers
    assert readyz() == {"status": "ready"}


def test_metrics_returns_prometheus_text(health_handlers):
    _, _, metrics = health_handlers
    response = metrics()
    body = response.body.decode("utf-8")

    assert "auth_register_total" in body
    assert "auth_login_total" in body
