# History

Newest entries first. Keep each entry to a few bullets, not a full diff.

## 2026-09-02 — Harness scaffolded

- Created the Python package (`reignit` CLI) with `init`, `refresh`, `serve`, and `show`.
- Proxy on :11444 presents as Ollama (`GET /` → `Ollama is running`) and as OpenAI (`/v1/chat/completions`).
- Wiki injection on chat/generate: functionality + history + targeting instructions.
- `reignit init` writes `wiki/functionality.md` and `wiki/history.md` for new or existing projects; existing trees get a scanned module map and recent git subjects.
