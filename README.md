# ReignIt

Agentic harness for local models running with hardware maxed out.

When a coding model has to ingest a large tree before it can decide anything, a loaded machine spends most of its time rereading context. ReignIt sits in front of [Ollama](https://ollama.com) and injects a three-file project wiki on every prompt so the model can see what the app does, where development left off, and which module to open — without chewing the whole filebase.

```
editor / client  →  :11444 ReignIt  →  :11434 Ollama
                         ↑
                   wiki/current.md      ← live checklist
                   wiki/functionality.md
                   wiki/history.md
```

The harness presents as a normal LLM endpoint: Ollama's native API and the OpenAI-compatible `/v1` surface. VS Code (Continue, Cline), Aider, Open WebUI, and anything else that can point at a base URL can use it.

## The wiki

`reignit` auto-seeds three wiki files on **first request** (no manual init). Use `reinit` to regenerate from scratch.

| File | Role |
| --- | --- |
| `wiki/current.md` | **Live checklist** — goal, status, `- [ ]` / `- [x]` items. Update before code and after every step. |
| `wiki/functionality.md` | What the app does, plus a **module map** (name, path, key files). |
| `wiki/history.md` | **Log** of completed units only — not the live checklist. |

The model is instructed to (Agent mode):

1. Read **current.md first** every turn — resume from the first unchecked item.
2. **Write current.md before implementing** — goal + checklist.
3. **Check off after each step** — mark `- [x]` immediately in current.md.
4. **Pivot in current.md** if the plan changes.
5. Update `functionality.md` when behavior or modules change.
6. Prepend finished work to `history.md`; reset `current.md` to idle.

On first request to a workspace, the harness writes default wiki files (scanning the tree if the repo already exists). Use `reinit` to regenerate both files from scratch.

## Install

Requires [uv](https://docs.astral.sh/uv/), Python 3.11+, and Ollama on the home server.

```bash
uv sync
```

Edit `reignit.toml` once (IPs, ports, Ollama URL). Always run commands from the ReignIt repo root.

## Usage

```bash
uv run reignit serve                              # start harness
uv run reignit reinit /path/to/repo               # regenerate wiki from scratch
uv run reignit refresh /path/to/repo              # rescan module map only
uv run reignit show /path/to/repo                 # preview injected wiki
```

No manual init. The first chat request with `?workspace=/path/on/server` creates `wiki/` if missing.

Each repo keeps its own `wiki/*.md`. The harness loads them **per request**.

### Home server (192.168.1.200)

Run ReignIt on the same machine as Ollama. Set addresses in `reignit.toml`:

```toml
host = "0.0.0.0"
port = 11444
public_url = "http://192.168.1.200:11444"
ollama = "http://192.168.1.200:11434"
```

```bash
uv run reignit serve    # one process, all repos — wiki auto-seeded per workspace
```

Clients on other machines (VS Code, Claude Code, Continue) point at `http://192.168.1.200:11444` with `?workspace=/path/on/server`.

### Which repo's wiki?

Paths must exist **on the server** (where ReignIt runs). Resolved per request, in order:

1. **`model@/path` in the model id** — best for VS Code (`qwen3.8:27b@/srv/repos/myapp`)
2. `X-ReignIt-Workspace: /srv/repos/myapp` header
3. `"reignit_workspace": "/srv/repos/myapp"` in the JSON body
4. `?workspace=/srv/repos/myapp` query parameter (avoid in VS Code `url` — causes 405 probes)
5. optional fallback: `workspace` in `reignit.toml`

If none is given, the request still reaches Ollama but the wiki block says "no workspace configured".

**VS Code Insiders** — base URL without query params; encode the server repo path in `id`:

```json
{
  "name": "ReignIt — myapp",
  "vendor": "customoai",
  "models": [{
    "name": "Qwen 3.8 27b",
    "url": "http://192.168.1.200:11444/v1",
    "id": "qwen3.8:27b@/srv/repos/myapp"
  }]
}
```

Do **not** put `?workspace=` in the VS Code `url` field — Insiders probes `/v1/chat/completions` with GET and used to get **405 method not allowed** (now handled by ReignIt, but `model@path` is still the reliable way to pass workspace).

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
4. optional fallback: `workspace` in `reignit.toml`

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
