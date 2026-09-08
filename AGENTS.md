# ReignIt

- Run all commands from the **ReignIt repo root** (where `reignit.toml` lives).
- Network settings (`host`, `port`, `public_url`, `upstream`/`ollama`, optional `api_key`) go in **`reignit.toml` only** — not env vars, not CLI flags.
- **Project path is per request** — `model@/path`, `X-ReignIt-Workspace`, or `reignit_workspace` in JSON.
- ReignIt runs on the **dev machine**; upstream LLM may be Ollama, vLLM, or a paid OpenAI-compatible API.
- Wiki auto-seeds on first request per project; use `reinit` to regenerate from scratch.
- Agent mode wiki loop: **current.md** is the live checklist; update before code and after each step. history.md is log-only.
