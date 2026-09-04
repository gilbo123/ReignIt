from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse

from reignit import SKIP_WIKI_HEADER, WORKSPACE_HEADER, __version__
from reignit.config import Settings, load_settings
from reignit.constants import HOP_BY_HOP, INJECT_PATHS
from reignit.inject import (
    build_wiki_block,
    inject_body,
    resolve_workspace,
    strip_reignit_fields,
    wiki_for_workspace,
    workspace_from_body,
)
from reignit.wiki import load_wiki


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
        # Continue, Cline, and other Ollama clients probe this string.
        return PlainTextResponse("Ollama is running")

    @app.head("/")
    async def root_head() -> Response:
        return Response(status_code=200)

    @app.get("/health")
    async def health() -> JSONResponse:
        ollama_ok, ollama_detail = await _ollama_status(app.state.http)
        workspace = settings.workspace
        wiki = load_wiki(workspace) if workspace else None
        return JSONResponse(
            {
                "status": "ok" if ollama_ok else "degraded",
                "harness": "reignit",
                "version": __version__,
                "ollama": settings.ollama_base(),
                "ollama_reachable": ollama_ok,
                "ollama_detail": ollama_detail,
                "workspace": str(workspace) if workspace else None,
                "wiki_present": bool(wiki and wiki.present),
            }
        )

    @app.get("/reignit")
    async def about() -> JSONResponse:
        return JSONResponse(
            {
                "name": "reignit",
                "version": __version__,
                "ollama": settings.ollama_base(),
                "workspace": str(settings.workspace) if settings.workspace else None,
                "wiki_files": ["wiki/functionality.md", "wiki/history.md"],
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
    inbound = await request.body()
    skip_wiki = _skip_wiki(request)
    method = request.method.upper()
    target_path = path if path.startswith("/") else f"/{path}"

    outbound = strip_reignit_fields(inbound)
    if not skip_wiki and (method, target_path) in INJECT_PATHS:
        workspace = resolve_workspace(
            request.headers.get(WORKSPACE_HEADER),
            request.query_params.get("workspace"),
            workspace_from_body(inbound),
            settings.workspace,
        )
        wiki = wiki_for_workspace(workspace)
        outbound = inject_body(outbound, build_wiki_block(wiki, workspace), target_path)

    headers = _filter_headers(request.headers.items())
    url = httpx.URL(path=target_path, query=request.url.query.encode("utf-8") or None)

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


def _skip_wiki(request: Request) -> bool:
    value = request.headers.get(SKIP_WIKI_HEADER, "").strip().lower()
    return value in {"0", "false", "no", "off"}


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


def default_workspace(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.expanduser().resolve()
    return None
