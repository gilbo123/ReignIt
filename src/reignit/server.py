from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse

from reignit import SKIP_WIKI_HEADER, WORKSPACE_HEADER, __version__
from reignit.config import Settings, load_settings
from reignit.constants import HOP_BY_HOP, INJECT_SUFFIXES
from reignit.inject import (
    build_wiki_block,
    inject_body,
    prepare_for_ollama,
    resolve_workspace,
    should_inject,
    wiki_for_workspace,
    workspace_from_body,
    workspace_from_model,
)

# VS Code probes POST-only OpenAI paths with GET; Ollama returns 405.
_POST_ONLY_SUFFIXES = INJECT_SUFFIXES


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.http = httpx.AsyncClient(
            base_url=settings.ollama_base(),
            timeout=httpx.Timeout(None),
            follow_redirects=True,
        )
        yield
        await app.state.http.aclose()

    app = FastAPI(title="ReignIt", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> PlainTextResponse:
        return PlainTextResponse("Ollama is running")

    @app.head("/")
    async def root_head() -> Response:
        return Response(status_code=200)

    @app.get("/health")
    async def health() -> JSONResponse:
        ollama_ok, ollama_detail = await _ollama_status(app.state.http)
        return JSONResponse(
            {
                "status": "ok" if ollama_ok else "degraded",
                "harness": "reignit",
                "version": __version__,
                "ollama": settings.ollama_base(),
                "ollama_reachable": ollama_ok,
                "ollama_detail": ollama_detail,
                "api_key_configured": bool(settings.api_key),
            }
        )

    @app.get("/reignit")
    async def about() -> JSONResponse:
        return JSONResponse(
            {
                "name": "reignit",
                "version": __version__,
                "ollama": settings.ollama_base(),
                "wiki_files": [
                    "wiki/current.md",
                    "wiki/functionality.md",
                    "wiki/history.md",
                ],
            }
        )

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def proxy(path: str, request: Request) -> Response:
        return await _forward(app, request, f"/{path}")

    return app


async def _forward(app: FastAPI, request: Request, path: str) -> Response:
    settings: Settings = app.state.settings
    client: httpx.AsyncClient = app.state.http
    method = request.method.upper()
    target_path = path if path.startswith("/") else f"/{path}"

    if _is_post_only_probe(method, target_path):
        return _probe_ok(method)

    inbound = await request.body()
    skip_wiki = _skip_wiki(request)
    workspace = resolve_workspace(
        workspace_from_model(inbound),
        request.headers.get(WORKSPACE_HEADER),
        workspace_from_body(inbound),
        request.query_params.get("workspace"),
    )

    outbound = prepare_for_ollama(inbound)
    if not skip_wiki and should_inject(method, target_path):
        wiki = wiki_for_workspace(workspace)
        outbound = inject_body(
            outbound,
            build_wiki_block(wiki, workspace),
            target_path,
            workspace,
        )

    headers = _upstream_headers(request, settings)
    url = httpx.URL(path=target_path, query=_ollama_query(request))

    try:
        upstream = await client.send(
            client.build_request(method, url, headers=headers, content=outbound),
            stream=True,
        )
    except httpx.ConnectError:
        return JSONResponse(
            {
                "error": {
                    "message": (
                        f"Cannot reach Ollama at {settings.ollama_base()}. "
                        "Check ollama in reignit.toml."
                    ),
                    "type": "connection_error",
                }
            },
            status_code=502,
        )
    except httpx.RequestError as exc:
        return JSONResponse(
            {
                "error": {
                    "message": f"Ollama request failed: {exc}",
                    "type": "proxy_error",
                }
            },
            status_code=502,
        )

    async def stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()

    return StreamingResponse(
        stream(),
        status_code=upstream.status_code,
        headers=_filter_headers(upstream.headers.items()),
        media_type=upstream.headers.get("content-type"),
    )


def _is_post_only_probe(method: str, path: str) -> bool:
    if method not in {"GET", "HEAD", "OPTIONS"}:
        return False
    return any(path.endswith(suffix) for suffix in _POST_ONLY_SUFFIXES)


def _probe_ok(method: str) -> Response:
    if method == "OPTIONS":
        return Response(status_code=204, headers={"Allow": "POST, OPTIONS"})
    if method == "HEAD":
        return Response(status_code=200)
    return JSONResponse({"object": "list", "data": []})


def _ollama_query(request: Request) -> bytes | None:
    pairs = [(k, v) for k, v in parse_qsl(request.url.query) if k != "workspace"]
    if not pairs:
        return None
    return urlencode(pairs).encode("utf-8")


def _skip_wiki(request: Request) -> bool:
    value = request.headers.get(SKIP_WIKI_HEADER, "").strip().lower()
    return value in {"0", "false", "no", "off"}


def _upstream_headers(request: Request, settings: Settings) -> dict[str, str]:
    headers = _filter_headers(request.headers.items())
    if settings.api_key and not any(key.lower() == "authorization" for key in headers):
        headers["authorization"] = f"Bearer {settings.api_key}"
    return headers


def _filter_headers(items: list[tuple[str, str]] | object) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for key, value in items:
        if key.lower() in HOP_BY_HOP:
            continue
        filtered[key] = value
    return filtered


async def _ollama_status(client: httpx.AsyncClient) -> tuple[bool, str]:
    try:
        response = await client.get("/")
    except httpx.RequestError as exc:
        return False, str(exc)
    return response.is_success, f"HTTP {response.status_code}"


def run(settings: Settings) -> None:
    import uvicorn

    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
