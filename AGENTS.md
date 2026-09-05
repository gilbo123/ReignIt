# ReignIt

- Run all commands from the **repo root** (where `reignit.toml` lives).
- Server settings go in **`reignit.toml` only** — not env vars, not CLI flags.
- Wiki auto-seeds on first request per workspace; use `reinit` to regenerate from scratch.
- Clients pass `?workspace=/path/on/server` — paths are on the home server, not the client Mac.
- Agent mode wiki loop: **current.md** is the live checklist; update before code and after each step. history.md is log-only.
