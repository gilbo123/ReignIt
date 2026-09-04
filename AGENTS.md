# ReignIt

- Run all commands from the **repo root** (where `reignit.toml` lives).
- Server settings go in **`reignit.toml` only** — not env vars, not CLI flags.
- Per-repo wikis: `uv run reignit init /path/to/repo` then clients pass `?workspace=` on each request.
