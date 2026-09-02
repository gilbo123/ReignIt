DEFAULT_PORT = 11444
DEFAULT_OLLAMA = "http://127.0.0.1:11434"
DEFAULT_HOST = "127.0.0.1"

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

HARNESS_INSTRUCTIONS = """You are working through ReignIt, a context harness for local models on limited hardware.

The wiki below is the source of truth for this project. Do not ingest the whole repository. Use the module map to open only the files that match the user's request.

How to work:
1. Read functionality.md (already included) to see what the app does and which module owns the request.
2. Read history.md (already included) to see where development left off.
3. Open only the paths listed for the target module(s). Example: "update the UI" means the ui module paths, not the whole tree.
4. After you change behavior or layout, update wiki/functionality.md so the overview and module map stay accurate.
5. After you finish a unit of work, prepend a short dated entry to wiki/history.md. A few bullets, not a diff.

Keep both wiki files short enough to reread on every fresh prompt.
"""
