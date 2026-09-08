# ReignIt

Agentic harness for local models running with hardware maxed out.

When a coding model has to ingest a large tree before it can decide anything, a loaded machine spends most of its time rereading context. ReignIt sits in front of your **upstream LLM** and injects a three-file project wiki on every prompt so the model can see what the app does, where development left off, and which module to open — without chewing the whole filebase.

```
editor / client  →  :11444 ReignIt (local, wiki)  →  upstream LLM (remote or local)
                         ↑
                   wiki/current.md      ← live checklist
                   wiki/functionality.md
                   wiki/history.md
```

ReignIt runs on your **dev machine** (where you edit code). Inference goes to whatever backend you configure — typically a remote GPU box, but also vLLM, or a paid OpenAI-compatible API.

The harness presents as a normal LLM endpoint: Ollama's native API and the OpenAI-compatible `/v1` surface. VS Code (Continue, Cline), Aider, Open WebUI, and anything else that can point at a base URL can use it.

## Getting started

1. **Clone ReignIt** on your dev machine (no GPU required here).

```bash
git clone …/ReignIt ~/git/ReignIt
cd ~/git/ReignIt
uv sync
```

2. **Edit `reignit.toml`** — set `upstream` to your LLM server:

```toml
host = "127.0.0.1"
port = 11444
public_url = "http://127.0.0.1:11444"
upstream = "http://192.168.1.200:11434"   # Ollama on a GPU box
# api_key = "sk-..."                      # optional — paid APIs
```

3. **Start the harness** (one process for all projects):

```bash
uv run reignit serve
```

4. **Point your editor** at the local harness and pass the **open project path** per request:

```json
{
  "url": "http://127.0.0.1:11444/v1",
  "id": "qwen3.8:27b@${workspaceFolder}"
}
```

Switch VS Code windows → different project wiki on the next chat, no restart.

The editor agent writes code and `wiki/` in whatever folder you have open. ReignIt reads the matching wiki when the request names that path.

## Which project?

Resolved **per request**, in order:

1. **`model@/path` in the model id** — best for VS Code (`qwen3.8:27b@${workspaceFolder}`)
2. `X-ReignIt-Workspace: /path/to/project` header
3. `"reignit_workspace": "/path/to/project"` in the JSON body
4. `?workspace=/path/to/project` query parameter (avoid in VS Code `url` — unnecessary)

Wiki files are auto-seeded on the **first request** for each path.

## The wiki

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

## Usage

Always run commands from the ReignIt repo root (where `reignit.toml` lives).

```bash
uv run reignit serve                    # start harness (all projects)
uv run reignit reinit /path/to/project  # regenerate wiki from scratch
uv run reignit refresh /path/to/project # rescan module map only
uv run reignit show /path/to/project    # preview injected wiki
```

### VS Code Insiders

```json
{
  "name": "ReignIt",
  "vendor": "customoai",
  "models": [{
    "name": "Qwen 3.8 27b",
    "url": "http://127.0.0.1:11444/v1",
    "id": "qwen3.8:27b@${workspaceFolder}",
    "toolCalling": true
  }]
}
```

Do **not** put `?workspace=` in the VS Code `url` field — Insiders probes `/v1/chat/completions` with GET (ReignIt handles this; use `model@path` instead).

### Other clients

**Continue** (`~/.continue/config.json`):

```json
{
  "models": [{
    "title": "ReignIt",
    "provider": "ollama",
    "model": "llama3.1",
    "apiBase": "http://127.0.0.1:11444"
  }]
}
```

**Cline / VS Code OpenAI-compatible providers:**

- Base URL: `http://127.0.0.1:11444/v1`
- API key: any non-empty string (Ollama ignores it)

**curl (OpenAI):**

```bash
curl http://127.0.0.1:11444/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1@/Users/you/git/MyApp","messages":[{"role":"user","content":"update the UI"}]}'
```

Send `X-ReignIt-Wiki: false` to pass a request through without wiki injection.

### Upstream backends

ReignIt proxies to whatever URL you set as `upstream` (or legacy `ollama`). Use the API surface your backend speaks:

| Backend | `upstream` example | Client path | Notes |
| --- | --- | --- | --- |
| [Ollama](https://ollama.com) | `http://192.168.1.200:11434` | `/v1/...` or `/api/...` | Default for local/remote GPUs |
| [vLLM](https://docs.vllm.ai/) | `http://gpu-box:8000` | `/v1/chat/completions` | OpenAI-compatible only |
| OpenAI / compatible APIs | `https://api.openai.com` | `/v1/chat/completions` | Set `api_key` in `reignit.toml` |

If `api_key` is set in `reignit.toml`, ReignIt sends `Authorization: Bearer …` on upstream requests **when the client did not already send one**. Client-provided keys always win.

### Endpoints

| Path | Behavior |
| --- | --- |
| `GET /` | `Ollama is running` — compatibility probe for Ollama-speaking clients |
| `GET /health` | Harness status and upstream reachability |
| `GET /v1/models`, `POST /v1/chat/completions` | OpenAI-compatible; wiki injected on chat/completions |
| `GET /api/tags`, `POST /api/chat`, `POST /api/generate` | Ollama-compatible; wiki injected on chat/generate |
| everything else | Proxied upstream as-is |

## Configuration

| Key | Example | Meaning |
| --- | --- | --- |
| `host` | `127.0.0.1` | Bind address |
| `port` | `11444` | Harness port |
| `public_url` | `http://127.0.0.1:11444` | URL your editor uses |
| `upstream` | `http://192.168.1.200:11434` | Upstream LLM base URL (alias: `ollama`) |
| `api_key` | `sk-…` | Optional bearer token for paid upstream APIs |

Network settings live in **`reignit.toml`** only — not env vars, not CLI flags. Do not commit real API keys.

Project path is **per request** — see [Which project?](#which-project) above.

## Development

```bash
uv sync
uv run pytest
```
