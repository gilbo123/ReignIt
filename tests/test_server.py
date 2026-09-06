from __future__ import annotations

import json
from dataclasses import replace
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

    def build_request(self, method, url, headers=None, content=None):
        self.last_content = content
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
    app = create_app(replace(settings, workspace=tmp_path))
    fake = _CapturingClient()
    with TestClient(app) as client:
        app.state.http = fake
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "llama3",
                "messages": [{"role": "user", "content": "update the UI"}],
            },
        )
    assert response.status_code == 200
    assert fake.last_content is not None
    forwarded = json.loads(fake.last_content)
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
