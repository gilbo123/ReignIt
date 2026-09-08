from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from reignit.config import Settings
from reignit.init_project import init_wiki
from reignit.server import create_app


class _FakeUpstream:
    def __init__(self, body: bytes = b'{"ok":true}') -> None:
        self.status_code = 200
        self.headers = httpx.Headers({"content-type": "application/json"})
        self._body = body

    async def aiter_raw(self):
        yield self._body

    async def aclose(self) -> None:
        return None


class _CapturingClient:
    def __init__(self) -> None:
        self.last_content: bytes | None = None
        self.last_headers: dict[str, str] | None = None

    def build_request(self, method, url, headers=None, content=None):
        self.last_content = content
        self.last_headers = dict(headers or {})
        return httpx.Request(method, "http://ollama.test/v1/chat/completions")

    async def send(self, request, stream=True):
        return _FakeUpstream()

    async def aclose(self) -> None:
        return None


def test_root_looks_like_ollama(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "Ollama is running"
        assert client.head("/").status_code == 200


def test_chat_completion_injects_wiki(tmp_path: Path, settings: Settings) -> None:
    init_wiki(tmp_path)
    app = create_app(settings)
    fake = _CapturingClient()
    project = str(tmp_path.resolve())
    with TestClient(app) as client:
        app.state.http = fake
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": f"llama3@{project}",
                "messages": [{"role": "user", "content": "update the UI"}],
            },
        )
    assert response.status_code == 200
    assert fake.last_content is not None
    forwarded = json.loads(fake.last_content)
    assert forwarded["model"] == "llama3"
    system = forwarded["messages"][0]
    assert system["role"] == "system"
    assert "BEGIN REIGNIT WIKI" in system["content"]
    assert "functionality.md" in system["content"]


def test_get_chat_completions_probe_ok(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/v1/chat/completions").status_code == 200
        assert client.get("/v1/chat/completions?workspace=/srv/a").status_code == 200
        assert client.options("/v1/chat/completions").status_code == 204


def test_health(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["api_key_configured"] is False
    assert "source" not in body


def test_api_key_from_settings_when_client_omits_auth(tmp_path: Path) -> None:
    init_wiki(tmp_path)
    settings = Settings(
        host="127.0.0.1",
        port=11444,
        ollama="http://127.0.0.1:11434",
        public_url="http://127.0.0.1:11444",
        api_key="sk-test-key",
    )
    app = create_app(settings)
    fake = _CapturingClient()
    with TestClient(app) as client:
        app.state.http = fake
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert response.status_code == 200
    assert fake.last_headers is not None
    assert fake.last_headers.get("authorization") == "Bearer sk-test-key"


def test_client_authorization_overrides_settings_api_key(tmp_path: Path) -> None:
    init_wiki(tmp_path)
    settings = Settings(
        host="127.0.0.1",
        port=11444,
        ollama="http://127.0.0.1:11434",
        public_url="http://127.0.0.1:11444",
        api_key="sk-from-config",
    )
    app = create_app(settings)
    fake = _CapturingClient()
    with TestClient(app) as client:
        app.state.http = fake
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-from-client"},
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert response.status_code == 200
    assert fake.last_headers is not None
    assert fake.last_headers.get("authorization") == "Bearer sk-from-client"
