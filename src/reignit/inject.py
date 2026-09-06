from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from reignit import CURRENT_FILE, WIKI_BEGIN, WIKI_END
from reignit.constants import HARNESS_INSTRUCTIONS, INJECT_SUFFIXES, USER_MANDATE
from reignit.init_project import ensure_wiki
from reignit.wiki import Wiki, load_wiki

logger = logging.getLogger(__name__)

_MODEL_WORKSPACE = re.compile(r"^(.+)@(/[^@]+)$")
_SYSTEM_ROLES = frozenset({"system", "developer"})


def should_inject(method: str, path: str) -> bool:
    if method != "POST":
        return False
    return any(path.endswith(suffix) for suffix in INJECT_SUFFIXES)


def resolve_workspace(*candidates: str | Path | None) -> Path | None:
    for raw in candidates:
        if raw is None:
            continue
        if isinstance(raw, Path):
            return raw.expanduser().resolve()
        text = raw.strip()
        if text:
            return Path(text).expanduser().resolve()
    return None


def workspace_from_body(body: bytes) -> str | None:
    payload = _parse_json(body)
    if not payload:
        return None
    raw = payload.get("reignit_workspace")
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def workspace_from_model(body: bytes) -> str | None:
    payload = _parse_json(body)
    if not payload:
        return None
    model = payload.get("model")
    if not isinstance(model, str):
        return None
    _, path = parse_model_workspace(model)
    return path


def parse_model_workspace(model: str) -> tuple[str, str | None]:
    match = _MODEL_WORKSPACE.match(model.strip())
    if not match:
        return model, None
    return match.group(1).strip(), match.group(2)


def prepare_for_ollama(body: bytes) -> bytes:
    payload = _parse_json(body)
    if not payload:
        return body
    changed = False
    if "reignit_workspace" in payload:
        del payload["reignit_workspace"]
        changed = True
    model = payload.get("model")
    if isinstance(model, str):
        clean, _ = parse_model_workspace(model)
        if clean != model:
            payload["model"] = clean
            changed = True
    if not changed:
        return body
    return json.dumps(payload).encode("utf-8")


def build_wiki_block(wiki: Wiki | None, workspace: Path | None) -> str:
    if workspace is None:
        return "\n".join(
            [
                WIKI_BEGIN,
                HARNESS_INSTRUCTIONS,
                "",
                "No workspace configured for this request.",
                "Set workspace in reignit.toml, ?workspace=, X-ReignIt-Workspace, reignit_workspace in JSON,",
                "or encode the server path in the model id: qwen3.8:27b@/srv/repos/myapp",
                WIKI_END,
            ]
        )

    if wiki is None or not wiki.present:
        return "\n".join(
            [
                WIKI_BEGIN,
                HARNESS_INSTRUCTIONS,
                "",
                f"Workspace: {workspace}",
                "Wiki files could not be loaded. Check that wiki/ is writable on the server.",
                WIKI_END,
            ]
        )

    wiki_root = wiki.root / "wiki"
    return "\n".join(
        [
            WIKI_BEGIN,
            HARNESS_INSTRUCTIONS,
            "",
            f"Workspace: {wiki.root}",
            f"Write these paths on disk: {wiki_root / CURRENT_FILE}, {wiki_root / 'functionality.md'}, {wiki_root / 'history.md'}",
            "",
            "## wiki/current.md  ← live checklist (update this most often)",
            "",
            wiki.current,
            "",
            "## wiki/functionality.md",
            "",
            wiki.functionality,
            "",
            "## wiki/history.md",
            "",
            wiki.history,
            "",
            WIKI_END,
        ]
    )


def inject_payload(
    payload: dict[str, Any],
    wiki_block: str,
    path: str,
    workspace: Path | None,
) -> dict[str, Any]:
    updated = deepcopy(payload)
    if path.endswith("/chat/completions") or path.endswith("/responses") or path.endswith("/api/chat"):
        _inject_messages(updated, wiki_block, workspace)
        if path.endswith("/api/chat"):
            _merge_ollama_system(updated, wiki_block)
    elif path.endswith("/completions") or path.endswith("/api/generate"):
        _inject_completion(updated, wiki_block)
    return updated


def inject_body(body: bytes, wiki_block: str, path: str, workspace: Path | None) -> bytes:
    payload = _parse_json(body)
    if not payload:
        return body
    updated = inject_payload(payload, wiki_block, path, workspace)
    return json.dumps(updated).encode("utf-8")


def wiki_for_workspace(workspace: Path | None) -> Wiki | None:
    if workspace is None:
        return None
    ensure_wiki(workspace)
    return load_wiki(workspace)


def _inject_messages(
    payload: dict[str, Any],
    wiki_block: str,
    workspace: Path | None,
) -> None:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        payload["messages"] = [{"role": "system", "content": wiki_block}]
        return

    injected_system = False
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") not in _SYSTEM_ROLES:
            continue
        content = _read_text(message.get("content"))
        if WIKI_BEGIN in content:
            messages[index] = {
                **message,
                "content": _replace_or_prepend(content, wiki_block),
            }
        else:
            messages[index] = {
                **message,
                "content": f"{wiki_block}\n\n{content}".strip(),
            }
        injected_system = True
        break

    if not injected_system:
        messages.insert(0, {"role": "system", "content": wiki_block})

    if workspace is not None:
        _prepend_user_mandate(messages, workspace)


def _prepend_user_mandate(messages: list[Any], workspace: Path) -> None:
    mandate = USER_MANDATE.format(
        workspace=workspace,
        current_file=workspace / "wiki" / CURRENT_FILE,
    )
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = _read_text(message.get("content"))
        if mandate.splitlines()[0] in content:
            return
        messages[index] = {
            **message,
            "content": f"{mandate}\n\n{content}".strip(),
        }
        return


def _merge_ollama_system(payload: dict[str, Any], wiki_block: str) -> None:
    existing = payload.get("system")
    if not isinstance(existing, str) or not existing.strip():
        payload["system"] = wiki_block
        return
    if WIKI_BEGIN in existing:
        payload["system"] = _replace_or_prepend(existing, wiki_block)
        return
    payload["system"] = f"{wiki_block}\n\n{existing}".strip()


def _inject_completion(payload: dict[str, Any], wiki_block: str) -> None:
    system = payload.get("system")
    if isinstance(system, str):
        if WIKI_BEGIN in system:
            payload["system"] = _replace_or_prepend(system, wiki_block)
        else:
            payload["system"] = f"{wiki_block}\n\n{system}".strip()
        return

    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        if WIKI_BEGIN in prompt:
            payload["prompt"] = _replace_or_prepend(prompt, wiki_block)
        else:
            payload["prompt"] = f"{wiki_block}\n\n{prompt}"
        return
    if isinstance(prompt, list):
        payload["prompt"] = [wiki_block, *prompt]


def _parse_json(body: bytes) -> dict[str, Any] | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _read_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def _replace_or_prepend(existing: str, wiki_block: str) -> str:
    start = existing.find(WIKI_BEGIN)
    end = existing.find(WIKI_END)
    if start >= 0 and end >= 0:
        end += len(WIKI_END)
        return f"{existing[:start]}{wiki_block}{existing[end:]}".strip()
    return f"{wiki_block}\n\n{existing}".strip()
