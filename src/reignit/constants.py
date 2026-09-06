DEFAULT_PORT = 11444

INJECT_SUFFIXES = (
    "/chat/completions",
    "/completions",
    "/api/chat",
    "/api/generate",
    "/responses",
)

USER_MANDATE = """[ReignIt] Workspace: {workspace}
FIRST ACTION: update {current_file} on disk (set _Status: in-progress_, goal, checklist) BEFORE any other file edit or tool use.
After each step: mark checklist items [x] in that same file."""

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

The wiki below is injected every turn. Do not ingest the whole repository.

## Every turn — read first
1. **wiki/current.md** — live goal, status, checklist (what is done vs pending).
2. **wiki/functionality.md** — what the app does, module map for targeting files.
3. **wiki/history.md** — completed work log (context only; not the live checklist).

## wiki/current.md — update BEFORE code, AFTER every step
This is the most important file. Keep it short. Write it to disk on the server every time it changes.

**Before any code change:**
- Set `_Status: in-progress_` and the goal.
- Add `- [ ]` items for this session.

**After each meaningful step** (do not wait until the task is finished):
- Mark the finished item `- [x]`.
- Add notes if the next step changed.

**If the plan pivots:** rewrite current.md immediately — set `_Status: pivoted_`, note why, replace the checklist.

**When the unit of work is done:**
- Prepend a short summary to wiki/history.md (Log).
- Reset current.md to `_Status: idle_`.

If you are cut off mid-task, the next session must resume from current.md alone.

## wiki/functionality.md
Update when behavior, layout, or module roles change.

Persist all wiki edits to disk under the workspace — they are re-read every turn.
"""
