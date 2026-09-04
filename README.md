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

Requires [uv](https://docs.astral.sh/uv/), Python 3.11+, and Ollama on the home server.

```bash
uv sync
```

Edit `reignit.toml` once (IPs, ports, Ollama URL), then:

```bash
uv run reignit serve
```

Always run from the ReignIt repo root — that is where `reignit.toml` lives.

## Usage

```bash
# Once per repo — creates wiki/functionality.md and wiki/history.md
uv run reignit init /path/to/repo

# Rescan modules after you add directories; keeps a hand-written overview
uv run reignit refresh /path/to/repo

# Start the home-server harness (no repo path needed)
uv run reignit serve

# Inspect what would be injected for a repo
uv run reignit show /path/to/repo
```

`init` is safe to run twice. Use `--force` only when you want both files regenerated.

Each repo keeps its own `wiki/*.md`. The harness loads them **per request** — it does not need a repo configured at serve time.

### Home server (192.168.1.200)

Run ReignIt on the same machine as Ollama. Set addresses in `reignit.toml`:

```toml
host = "0.0.0.0"
port = 11444
public_url = "http://192.168.1.200:11444"
ollama = "http://192.168.1.200:11434"
```

```bash
uv sync
uv run reignit init /srv/repos/myapp      # repeat for each repo
uv run reignit serve                      # one process, many repos
```

Clients on other machines point at `http://192.168.1.200:11444` and tell the harness **which repo's wiki** to load (see below).

### Which repo's wiki?

Paths must exist **on the server** (where ReignIt runs). Resolved per request, in order:

1. `?workspace=/srv/repos/myapp` on the URL — works in VS Code `chatLanguageModels.json`
2. `X-ReignIt-Workspace: /srv/repos/myapp` header
3. `"reignit_workspace": "/srv/repos/myapp"` in the JSON body (stripped before Ollama sees it)
4. optional fallback: `workspace` in `reignit.toml`

If none is given, the request still reaches Ollama but the wiki block says "no workspace configured".

**VS Code Insiders** — one model entry per repo, workspace in the URL:

```json
{
  "name": "ReignIt — myapp",
  "vendor": "customoai",
  "models": [{
    "name": "Qwen 3.8 27b",
    "url": "http://192.168.1.200:11444?workspace=/srv/repos/myapp",
    "id": "qwen3.8:27b"
  }]
}
```

Remove stray `customendpoint` / `apiType: "messages"` entries — ReignIt speaks OpenAI and Ollama APIs, not Anthropic Messages.

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

The wiki is read from a project directory on the **server**, resolved per request:

1. `?workspace=/path/to/project` query parameter (easiest for VS Code)
2. `X-ReignIt-Workspace: /path/to/project` request header
3. `"reignit_workspace": "/path/to/project"` in the JSON body
4. optional fallback: `--workspace` on `reignit serve` (or `REIGNIT_WORKSPACE`)

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

All server settings live in **`reignit.toml`** at the repo root. One file, no env vars, no CLI flags.

| Key | Example | Meaning |
| --- | --- | --- |
| `host` | `0.0.0.0` | Bind address |
| `port` | `11444` | Harness port |
| `public_url` | `http://192.168.1.200:11444` | URL clients on the LAN use |
| `ollama` | `http://192.168.1.200:11434` | Upstream Ollama |
| `workspace` | `/srv/repos/myapp` | Optional fallback wiki path |

## Development

```bash
uv sync
uv run pytest
```
