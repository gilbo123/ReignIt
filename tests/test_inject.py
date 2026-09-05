import json
from pathlib import Path

from reignit import WIKI_BEGIN, WIKI_END
from reignit.inject import (
    build_wiki_block,
    inject_payload,
    resolve_workspace,
    strip_reignit_fields,
    wiki_for_workspace,
    workspace_from_body,
)
from reignit.wiki import Wiki


def _wiki() -> Wiki:
    return Wiki(
        root=Path("/tmp/demo"),
        current="_Status: in-progress_\n\n- [x] read ui\n- [ ] wire form",
        functionality="## Modules\n\n### ui (`src/ui/`)\n",
        history="### 2026-09-01 — started",
    )


def test_inject_chat_completions_prepends_system() -> None:
    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": "update the UI"}],
    }
    result = inject_payload(payload, "WIKI", "/v1/chat/completions")
    assert result["messages"][0] == {"role": "system", "content": "WIKI"}
    assert result["messages"][1]["content"] == "update the UI"
    assert payload["messages"][0]["role"] == "user"


def test_inject_merges_existing_system() -> None:
    payload = {
        "messages": [
            {"role": "system", "content": "be concise"},
            {"role": "user", "content": "hi"},
        ]
    }
    result = inject_payload(payload, "WIKI", "/api/chat")
    assert result["messages"][0]["content"].startswith("WIKI")
    assert "be concise" in result["messages"][0]["content"]


def test_inject_replaces_stale_wiki_block() -> None:
    stale = f"{WIKI_BEGIN}\nold\n{WIKI_END}\n\nbe concise"
    payload = {"messages": [{"role": "system", "content": stale}]}
    result = inject_payload(payload, f"{WIKI_BEGIN}\nfresh\n{WIKI_END}", "/v1/chat/completions")
    content = result["messages"][0]["content"]
    assert "fresh" in content
    assert "old" not in content
    assert "be concise" in content


def test_inject_generate_sets_system() -> None:
    payload = {"model": "llama3", "prompt": "hello", "system": "base"}
    result = inject_payload(payload, "WIKI", "/api/generate")
    assert result["system"].startswith("WIKI")
    assert result["prompt"] == "hello"


def test_wiki_for_workspace_seeds_missing_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n")
    wiki = wiki_for_workspace(tmp_path)
    assert wiki is not None
    assert wiki.present
    assert (tmp_path / "wiki" / "current.md").is_file()
    assert (tmp_path / "wiki" / "functionality.md").is_file()
    assert (tmp_path / "wiki" / "history.md").is_file()
    assert "Current work" in wiki.current


def test_build_wiki_block_no_workspace() -> None:
    block = build_wiki_block(None, None)
    assert "No workspace configured" in block
    block = build_wiki_block(_wiki(), Path("/tmp/demo"))
    assert WIKI_BEGIN in block
    assert WIKI_END in block
    assert "wiki/current.md" in block
    assert "live checklist" in block
    assert "src/ui/" in block
    assert "2026-09-01" in block


def test_resolve_workspace_prefers_header() -> None:
    resolved = resolve_workspace("/from/header", "/from/query", "/from/body", Path("/from/default"))
    assert resolved == Path("/from/header").resolve()


def test_workspace_from_body() -> None:
    body = b'{"model":"x","reignit_workspace":"/srv/a","messages":[]}'
    assert workspace_from_body(body) == "/srv/a"


def test_strip_reignit_fields() -> None:
    body = b'{"model":"x","reignit_workspace":"/srv/a"}'
    cleaned = json.loads(strip_reignit_fields(body))
    assert "reignit_workspace" not in cleaned
    assert cleaned["model"] == "x"
