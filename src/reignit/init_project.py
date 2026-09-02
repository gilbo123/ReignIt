from __future__ import annotations

from pathlib import Path

from reignit.wiki import (
    functionality_path,
    history_path,
    refresh_functionality,
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
    """Create the two wiki files. Returns a map of relative path → action."""
    root = root.resolve()
    existing = is_existing_project(root)
    root.mkdir(parents=True, exist_ok=True)
    wiki_dir(root).mkdir(parents=True, exist_ok=True)

    actions: dict[str, str] = {}
    func = functionality_path(root)
    hist = history_path(root)

    func_existed = func.exists()
    if func_existed and not force:
        actions[str(func.relative_to(root))] = "exists"
    else:
        func.write_text(render_functionality(root), encoding="utf-8")
        actions[str(func.relative_to(root))] = "replaced" if func_existed else "created"

    hist_existed = hist.exists()
    if hist_existed and not force:
        actions[str(hist.relative_to(root))] = "exists"
    else:
        hist.write_text(render_history(root, existing_project=existing), encoding="utf-8")
        actions[str(hist.relative_to(root))] = "replaced" if hist_existed else "created"

    return actions


def refresh_wiki(root: Path) -> str:
    root = root.resolve()
    func = functionality_path(root)
    if not func.exists():
        raise FileNotFoundError(
            f"No {func.relative_to(root)} — run `reignit init` first."
        )
    updated = refresh_functionality(func.read_text(encoding="utf-8"), root)
    func.write_text(updated, encoding="utf-8")
    return str(func.relative_to(root))
