import asyncio
import importlib


def run_asgi_request(app, *, origin: str) -> tuple[int, dict[str, str]]:
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "OPTIONS",
        "scheme": "http",
        "path": "/orders",
        "raw_path": b"/orders",
        "query_string": b"",
        "headers": [
            (b"origin", origin.encode()),
            (b"access-control-request-method", b"POST"),
            (b"access-control-request-headers", b"content-type,authorization"),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    asyncio.run(app(scope, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]
    }
    return start["status"], headers


def test_cors_preflight_allows_configured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://frontend.example.com/")

    import app.config

    app.config.get_settings.cache_clear()
    import app.main

    importlib.reload(app.main)

    status, headers = run_asgi_request(
        app.main.app,
        origin="https://frontend.example.com",
    )

    assert status == 200
    assert headers["access-control-allow-origin"] == "https://frontend.example.com"
    assert headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_allows_public_origin_by_default(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    import app.config

    app.config.get_settings.cache_clear()
    import app.main

    importlib.reload(app.main)

    status, headers = run_asgi_request(
        app.main.app,
        origin="https://kubereats.click",
    )

    assert status == 200
    assert headers["access-control-allow-origin"] == "https://kubereats.click"

def test_cors_preflight_blocks_unconfigured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://frontend.example.com")

    import app.config

    app.config.get_settings.cache_clear()
    import app.main

    importlib.reload(app.main)

    status, headers = run_asgi_request(
        app.main.app,
        origin="https://evil.example.com",
    )

    assert status == 400
    assert "access-control-allow-origin" not in headers
