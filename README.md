# ReignIt

Agentic harness for local models running with hardware maxed out.

When a coding model has to ingest a large tree before it can decide anything, a loaded machine spends most of its time rereading context. ReignIt sits in front of [Ollama](https://ollama.com) and injects a two-file project wiki on every prompt so the model can see what the app does, where development left off, and which module to open — without chewing the whole filebase.

```
editor / client  →  :11444 ReignIt  →  :11434 Ollama
                         ↑
                   wiki/functionality.md
                   wiki/history.md
```

The harness presents as a normal LLM endpoint: Ollama's native API and the OpenAI-compatible `/v1` surface. VS Code (Continue, Cline), Aider, Open WebUI, and anything else that can point at a base URL can use it.

## The wiki

`reignit init` writes two files into the target project:

| File | Role |
| --- | --- |
| `wiki/functionality.md` | What the app does, plus a **module map** (name, path, key files). A prompt like "update the UI" should resolve to one module. |
| `wiki/history.md` | Short, newest-first development log — the same job as `git log`, small enough to reread on a fresh prompt. |

The model is instructed to:

1. Use the module map to open only the files that match the request.
2. Update `functionality.md` when behavior or layout changes.
3. Prepend a brief entry to `history.md` when a unit of work is done.

On an existing project, init scans the tree (skipping `node_modules`, `.venv`, and similar) and seeds the module map. If the repo has git history, recent commit subjects are copied into `history.md` for orientation.

## Install

Requires [uv](https://docs.astral.sh/uv/), Python 3.10+, and a running Ollama daemon (default `http://127.0.0.1:11434`).

```bash
uv sync
```

Run commands through uv (no manual venv activation needed):

```bash
uv run reignit --help
```

## Usage

```bash
# New or existing project — creates the two wiki files, does not overwrite
uv run reignit init /path/to/project

# Rescan modules after you add directories; keeps a hand-written overview
uv run reignit refresh /path/to/project

# Serve the harness (default workspace is injected when the client does not name one)
uv run reignit serve --workspace /path/to/project

# Inspect what would be injected
uv run reignit show /path/to/project
```

`init` is safe to run twice. Use `--force` only when you want both files regenerated.

### Point a client at the harness

Keep using your usual model name. Change only the base URL.

**Continue** (`~/.continue/config.json`):

```json
{
  "models": [
    {
      "title": "ReignIt",
      "provider": "ollama",
      "model": "llama3.1",
      "apiBase": "http://127.0.0.1:11444"
    }
  ]
}
```

**Cline / VS Code OpenAI-compatible providers:**

- Base URL: `http://127.0.0.1:11444/v1`
- API key: any non-empty string (Ollama ignores it)

**Aider:**

```bash
export OPENAI_API_BASE=http://127.0.0.1:11444/v1
export OPENAI_API_KEY=ollama
aider --model openai/llama3.1
```

**curl (OpenAI):**

```bash
curl http://127.0.0.1:11444/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1","messages":[{"role":"user","content":"update the UI"}]}'
```

**curl (Ollama):**

```bash
curl http://127.0.0.1:11444/api/chat \
  -d '{"model":"llama3.1","messages":[{"role":"user","content":"where did we leave off?"}]}'
```

### Workspace selection

The wiki is read from a project directory, resolved in this order:

1. `X-ReignIt-Workspace: /path/to/project` request header
2. `?workspace=/path/to/project` query parameter
3. `--workspace` on `reignit serve` (or `REIGNIT_WORKSPACE`)

Send `X-ReignIt-Wiki: false` to pass a request through untouched.

### Endpoints

| Path | Behavior |
| --- | --- |
| `GET /` | `Ollama is running` — so Ollama-speaking clients accept the port |
| `GET /health` | Harness status, Ollama reachability, wiki presence |
| `GET /v1/models`, `POST /v1/chat/completions` | OpenAI-compatible; wiki injected on chat/completions |
| `GET /api/tags`, `POST /api/chat`, `POST /api/generate` | Ollama-compatible; wiki injected on chat/generate |
| everything else | Proxied to Ollama as-is (`/api/show`, embeddings, pull, …) |

## Configuration

Environment variables (prefix `REIGNIT_`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `REIGNIT_HOST` | `127.0.0.1` | Bind address |
| `REIGNIT_PORT` | `11444` | Harness port |
| `REIGNIT_OLLAMA` | `http://127.0.0.1:11434` | Upstream Ollama |
| `REIGNIT_WORKSPACE` | unset | Default project for wiki injection |

## Development

```bash
uv sync
uv run pytest
```
