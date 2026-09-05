from __future__ import annotations

from pathlib import Path

from reignit.wiki import (
    current_path,
    functionality_path,
    history_path,
    refresh_functionality,
    render_current,
    render_functionality,
    render_history,
    wiki_dir,
)


def is_existing_project(root: Path) -> bool:
    if not root.exists():
        return False
    try:
        entries = list(root.iterdir())
    except OSError:
        return False
    ignore = {".git", ".gitignore", ".DS_Store", "wiki", ".reignit"}
    return any(item.name not in ignore for item in entries)


def init_wiki(root: Path, *, force: bool = False) -> dict[str, str]:
    """Create wiki files. Returns a map of relative path → action."""
    root = root.resolve()
    existing = is_existing_project(root)
    root.mkdir(parents=True, exist_ok=True)
    wiki_dir(root).mkdir(parents=True, exist_ok=True)

    actions: dict[str, str] = {}
    files = (
        (functionality_path(root), render_functionality(root)),
        (current_path(root), render_current()),
        (history_path(root), render_history(root, existing_project=existing)),
    )

    for path, content in files:
        existed = path.exists()
        if existed and not force:
            actions[str(path.relative_to(root))] = "exists"
        else:
            path.write_text(content, encoding="utf-8")
            actions[str(path.relative_to(root))] = "replaced" if existed else "created"

    return actions


def ensure_wiki(root: Path) -> dict[str, str]:
    """Create missing wiki files from defaults. Never overwrites existing content."""
    return init_wiki(root, force=False)


def refresh_wiki(root: Path) -> str:
    root = root.resolve()
    ensure_wiki(root)
    func = functionality_path(root)
    updated = refresh_functionality(func.read_text(encoding="utf-8"), root)
    func.write_text(updated, encoding="utf-8")
    return str(func.relative_to(root))
