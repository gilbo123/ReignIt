from __future__ import annotations

import json
from pathlib import Path

from reignit.constants import (
    MANIFEST_HINTS,
    MAX_FILES_PER_DIR,
    MAX_MODULES,
    MAX_SCAN_DEPTH,
    SKIP_DIRS,
    SKIP_FILES,
)


def infer_project_kind(root: Path) -> str:
    matches: list[str] = []
    for filename, label in MANIFEST_HINTS:
        if (root / filename).exists():
            matches.append(label)
    if not matches:
        return "unknown"
    # Preserve order, drop duplicates.
    seen: list[str] = []
    for item in matches:
        if item not in seen:
            seen.append(item)
    return ", ".join(seen)


def infer_overview(root: Path, kind: str) -> str:
    readme = _first_readme(root)
    if readme:
        snippet = _first_paragraph(readme)
        if snippet:
            return snippet
    name = root.name
    if kind != "unknown":
        return f"{name} looks like a {kind} project. Replace this sentence with what the application does."
    return f"{name} is a new project. Describe what this application does here."


def scan_modules(root: Path) -> list[dict]:
    """Walk a shallow tree and return module dicts: name, path, files."""
    modules: list[dict] = []
    for child in _sorted_entries(root):
        if _skip_entry(child):
            continue
        rel = child.relative_to(root).as_posix()
        if child.is_file():
            continue
        files = _collect_files(child, root, depth=1)
        if not files and not any(p.is_dir() and not _skip_entry(p) for p in child.iterdir()):
            continue
        modules.append(
            {
                "name": child.name,
                "path": f"{rel}/",
                "files": files,
            }
        )
        if len(modules) >= MAX_MODULES:
            break

    if not modules:
        top_files = [
            p.relative_to(root).as_posix()
            for p in _sorted_entries(root)
            if p.is_file() and not _skip_entry(p) and p.name.lower() not in {"license", "licence"}
        ][:MAX_FILES_PER_DIR]
        if top_files:
            modules.append({"name": "root", "path": ".", "files": top_files})
    return modules


def _collect_files(directory: Path, root: Path, depth: int) -> list[str]:
    files: list[str] = []
    try:
        entries = _sorted_entries(directory)
    except OSError:
        return files

    for entry in entries:
        if _skip_entry(entry):
            continue
        if entry.is_file():
            files.append(entry.relative_to(root).as_posix())
            if len(files) >= MAX_FILES_PER_DIR:
                return files
        elif entry.is_dir() and depth < MAX_SCAN_DEPTH:
            nested = _collect_files(entry, root, depth + 1)
            for item in nested:
                files.append(item)
                if len(files) >= MAX_FILES_PER_DIR:
                    return files
    return files


def _sorted_entries(path: Path) -> list[Path]:
    try:
        return sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return []


def _skip_entry(path: Path) -> bool:
    name = path.name
    if name in SKIP_DIRS or name.lower() in SKIP_FILES:
        return True
    if name.startswith(".") and name not in {".github"}:
        return True
    return False


def _first_readme(root: Path) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        candidate = root / name
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError:
                return None
    return None


def _first_paragraph(text: str) -> str:
    lines: list[str] = []
    started = False
    for raw in text.splitlines():
        line = raw.strip()
        if not started:
            if not line or line.startswith("#") or line.startswith("==") or line.startswith("--"):
                continue
            started = True
        if started:
            if not line:
                break
            lines.append(line)
    return " ".join(lines).strip()


def package_json_name(root: Path) -> str | None:
    manifest = root / "package.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    name = data.get("name")
    return name if isinstance(name, str) else None
