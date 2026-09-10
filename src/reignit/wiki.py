from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from reignit import CURRENT_FILE, FUNCTIONALITY_FILE, HISTORY_FILE, WIKI_DIR
from reignit.scan import infer_overview, infer_project_kind, scan_modules

MODULES_START = "<!-- reignit:modules:start -->"
MODULES_END = "<!-- reignit:modules:end -->"


@dataclass(frozen=True)
class Wiki:
    root: Path
    current: str
    functionality: str
    history: str
    missing: tuple[str, ...] = ()
    freshly_seeded: bool = False

    @property
    def present(self) -> bool:
        return not self.missing


def wiki_dir(root: Path) -> Path:
    return root / WIKI_DIR


def current_path(root: Path) -> Path:
    return wiki_dir(root) / CURRENT_FILE


def functionality_path(root: Path) -> Path:
    return wiki_dir(root) / FUNCTIONALITY_FILE


def history_path(root: Path) -> Path:
    return wiki_dir(root) / HISTORY_FILE


def load_wiki(root: Path) -> Wiki:
    root = root.resolve()
    missing: list[str] = []
    current = ""
    functionality = ""
    history = ""

    for path, store in (
        (current_path(root), "current"),
        (functionality_path(root), "functionality"),
        (history_path(root), "history"),
    ):
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if store == "current":
                current = text
            elif store == "functionality":
                functionality = text
            else:
                history = text
        else:
            missing.append(str(path))

    return Wiki(
        root=root,
        current=current,
        functionality=functionality,
        history=history,
        missing=tuple(missing),
    )


def render_functionality_placeholder(name: str) -> str:
    return "\n".join(
        [
            f"# Functionality — {name}",
            "",
            "_Describe what this application does. The agent should fill this in from the open project._",
        ]
    )


def render_history_placeholder() -> str:
    return "\n".join(
        [
            "# History",
            "",
            "Completed work only — newest first. Active checklist lives in `wiki/current.md`.",
        ]
    )


def render_current() -> str:
    return "\n".join(
        [
            "# Current work",
            "",
            "_Status: idle_",
            "",
            "_Live checklist — update this file before code changes and after each step._",
            "",
            "Goal:",
            "",
            "- [ ]",
        ]
    )


def wiki_for_injection(root: Path) -> Wiki:
    """Wiki content to inject. Seeds missing wiki/ on disk when the workspace exists."""
    from reignit.init_project import ensure_wiki

    root = root.resolve()
    if root.is_dir():
        actions = ensure_wiki(root)
        freshly_seeded = any(action == "created" for action in actions.values())
        loaded = load_wiki(root)
        if loaded.present:
            return Wiki(
                root=loaded.root,
                current=loaded.current,
                functionality=loaded.functionality,
                history=loaded.history,
                missing=loaded.missing,
                freshly_seeded=freshly_seeded,
            )
    return Wiki(
        root=root,
        current=render_current(),
        functionality=render_functionality(root) if root.is_dir() else render_functionality_placeholder(root.name),
        history=render_history(root, existing_project=root.is_dir()) if root.is_dir() else render_history_placeholder(),
        freshly_seeded=False,
    )


def render_functionality(root: Path, overview: str | None = None) -> str:
    kind = infer_project_kind(root)
    body_overview = overview if overview is not None else infer_overview(root, kind)
    modules = scan_modules(root)
    return _compose_functionality(root.name, kind, body_overview, modules)


def render_history(root: Path, *, existing_project: bool) -> str:
    today = date.today().isoformat()
    kind = infer_project_kind(root)
    commits = recent_git_subjects(root, limit=8)
    lines = [
        "# History",
        "",
        "Completed work only — newest first. Active checklist lives in `wiki/current.md`.",
        "",
        f"### {today} — Wiki initialized",
        f"- Created `{WIKI_DIR}/{CURRENT_FILE}`, `{FUNCTIONALITY_FILE}`, `{HISTORY_FILE}`.",
        f"- Project type: {kind}.",
    ]
    if existing_project:
        lines.append("- Existing project scanned for a module map.")
    else:
        lines.append("- Empty or new project; module map is a starter template.")
    if commits:
        lines.append("")
        lines.append("Recent commits at init (for orientation):")
        for subject in commits:
            lines.append(f"- {subject}")
    lines.append("")
    return "\n".join(lines)


def refresh_functionality(existing: str, root: Path) -> str:
    """Replace the generated module map, keep the human-written overview."""
    overview = _extract_overview(existing) or infer_overview(root, infer_project_kind(root))
    return render_functionality(root, overview=overview)


def recent_git_subjects(root: Path, limit: int = 8) -> list[str]:
    git_dir = root / ".git"
    if not git_dir.exists():
        return []
    try:
        import subprocess

        result = subprocess.run(
            ["git", "-C", str(root), "log", f"-{limit}", "--pretty=format:%h %s"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _compose_functionality(name: str, kind: str, overview: str, modules: list[dict]) -> str:
    lines = [
        f"# Functionality — {name}",
        "",
        f"_Project type: {kind}_",
        "",
        "## Overview",
        "",
        overview,
        "",
        "## How to target work",
        "",
        "Match the user's request to a module below, then open only that module's paths.",
        "Examples: \"update the UI\" → `ui`. \"fix the API\" → `api` or `server`. \"change the schema\" → `db` / `models`.",
        "",
        "## Modules",
        "",
        MODULES_START,
        "",
    ]
    if not modules:
        lines.extend(
            [
                "_No modules detected yet. Add an entry when you create the first directory._",
                "",
                "### example-ui (`src/ui/`)",
                "",
                "User interface. Read these files when the user asks to change how the app looks.",
                "",
            ]
        )
    else:
        for module in modules:
            lines.append(f"### {module['name']} (`{module['path']}`)")
            lines.append("")
            lines.append(f"Owns `{module['path']}`. Describe this module's role here.")
            files = module.get("files") or []
            if files:
                lines.append("")
                lines.append("Key paths:")
                for file_path in files:
                    lines.append(f"- `{file_path}`")
            lines.append("")
    lines.extend([MODULES_END, ""])
    return "\n".join(lines)


def _extract_overview(text: str) -> str | None:
    marker = "## Overview"
    start = text.find(marker)
    if start < 0:
        return None
    rest = text[start + len(marker) :]
    next_heading = rest.find("\n## ")
    chunk = rest if next_heading < 0 else rest[:next_heading]
    overview = "\n".join(
        line for line in chunk.strip().splitlines() if line.strip()
    ).strip()
    return overview or None
