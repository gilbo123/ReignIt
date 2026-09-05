DEFAULT_PORT = 11444

INJECT_PATHS = {
    ("POST", "/v1/chat/completions"),
    ("POST", "/v1/completions"),
    ("POST", "/api/chat"),
    ("POST", "/api/generate"),
}

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".cursor",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tox",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "target",
    "vendor",
    "coverage",
    "htmlcov",
    "eggs",
    ".eggs",
    "wiki",
    ".reignit",
}

SKIP_FILES = {
    ".ds_store",
    "thumbs.db",
}

MANIFEST_HINTS = (
    ("package.json", "Node.js / JavaScript"),
    ("pnpm-workspace.yaml", "Node.js workspace"),
    ("pyproject.toml", "Python"),
    ("requirements.txt", "Python"),
    ("Cargo.toml", "Rust"),
    ("go.mod", "Go"),
    ("composer.json", "PHP"),
    ("Gemfile", "Ruby"),
    ("pom.xml", "Java (Maven)"),
    ("build.gradle", "Java / Kotlin (Gradle)"),
    ("build.gradle.kts", "Kotlin (Gradle)"),
    ("CMakeLists.txt", "C / C++"),
    ("mix.exs", "Elixir"),
)

MAX_SCAN_DEPTH = 3
MAX_FILES_PER_DIR = 24
MAX_MODULES = 40

HARNESS_INSTRUCTIONS = """You are working through ReignIt in Agent mode on limited hardware.

The wiki below is injected every turn and is the source of truth. Do not ingest the whole repository. Use the module map in functionality.md to open only files that match the request.

## Every turn — read first
1. functionality.md — what the app does, which module owns the request.
2. history.md — especially **Current work**: goal, checklist, what is done vs pending.

## Before implementing anything — write first
Update wiki/history.md **before** editing code:
- Set **Current work** goal and a `- [ ]` checklist for this session.
- If resuming, read the checklist and continue from the first unchecked item.
- If the approach changed, rewrite **Current work** immediately (note *pivoted* and why). Do not leave a stale plan.

## While working — check off as you go
After each meaningful step (not at the end of the whole task):
- Mark the item `- [x]` in **Current work**.
- Add a one-line note if the next step changed.
- Update wiki/functionality.md if behavior, layout, or module roles changed.

Do not batch wiki updates until everything is finished. If you are cut off mid-task, the next session must be able to read **Current work** and know exactly what landed and what is left.

## When a unit of work is fully done
- Move a short summary from **Current work** into **Log** (newest first, dated).
- Clear or reset **Current work** to `_Status: idle_` unless a new goal starts immediately.

Keep both wiki files concise. Prefer updating **Current work** over long log entries during active development.
"""
