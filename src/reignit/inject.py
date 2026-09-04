from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from reignit import WIKI_BEGIN, WIKI_END
from reignit.constants import HARNESS_INSTRUCTIONS
from reignit.wiki import Wiki, load_wiki


def resolve_workspace(
    header_value: str | None,
    query_value: str | None,
    body_value: str | None,
    default: Path | None,
) -> Path | None:
    for raw in (header_value, query_value, body_value):
        if raw:
            return Path(raw).expanduser().resolve()
    if default is not None:
        return default.expanduser().resolve()
    return None


def workspace_from_body(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    raw = payload.get("reignit_workspace")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def strip_reignit_fields(body: bytes) -> bytes:
    if not body:
        return body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if not isinstance(payload, dict) or "reignit_workspace" not in payload:
        return body
    cleaned = {key: value for key, value in payload.items() if key != "reignit_workspace"}
    return json.dumps(cleaned).encode("utf-8")


def build_wiki_block(wiki: Wiki | None, workspace: Path | None) -> str:
    if wiki is None or not wiki.present:
        location = str(workspace) if workspace else "(no workspace configured)"
        return "\n".join(
            [
                WIKI_BEGIN,
                HARNESS_INSTRUCTIONS,
                "",
                f"No wiki found for workspace: {location}",
                "Run `reignit init` in the project so functionality.md and history.md exist.",
                WIKI_END,
            ]
        )

    return "\n".join(
        [
            WIKI_BEGIN,
            HARNESS_INSTRUCTIONS,
            "",
            f"Workspace: {wiki.root}",
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


def inject_payload(payload: dict[str, Any], wiki_block: str, path: str) -> dict[str, Any]:
    updated = deepcopy(payload)
    if path.endswith("/chat/completions") or path.endswith("/api/chat"):
        _inject_messages(updated, wiki_block)
        if path.endswith("/api/chat"):
            _merge_ollama_system(updated, wiki_block)
    elif path.endswith("/completions") or path.endswith("/api/generate"):
        _inject_completion(updated, wiki_block)
    return updated


def inject_body(body: bytes, wiki_block: str, path: str) -> bytes:
    if not body:
        return body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if not isinstance(payload, dict):
        return body
    updated = inject_payload(payload, wiki_block, path)
    return json.dumps(updated).encode("utf-8")


def wiki_for_workspace(workspace: Path | None) -> Wiki | None:
    if workspace is None:
        return None
    return load_wiki(workspace)


def _inject_messages(payload: dict[str, Any], wiki_block: str) -> None:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        payload["messages"] = [{"role": "system", "content": wiki_block}]
        return

    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "system":
            continue
        content = _read_text(message.get("content"))
        if WIKI_BEGIN in content:
            messages[index] = {
                **message,
                "content": _replace_or_prepend(content, wiki_block),
            }
            return
        messages[index] = {
            **message,
            "content": f"{wiki_block}\n\n{content}".strip(),
        }
        return

    messages.insert(0, {"role": "system", "content": wiki_block})


def _merge_ollama_system(payload: dict[str, Any], wiki_block: str) -> None:
    existing = payload.get("system")
    if not isinstance(existing, str) or not existing.strip():
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
