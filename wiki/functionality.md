# Functionality — ReignIt

_Project type: Python_

## Overview

ReignIt is a wiki-backed LLM harness. It listens on port 11444, speaks both the Ollama native API and the OpenAI-compatible `/v1` surface, and forwards generation to Ollama on 11434. Before each generate/chat call it injects two project files — `wiki/functionality.md` and `wiki/history.md` — so a hardware-constrained local model can see what the app does, where work left off, and which module to open, without ingesting the whole tree.

## How to target work

Match the user's request to a module below, then open only that module's paths.
Examples: "update the UI" → `ui`. "fix the API" → `api` or `server`. "change the schema" → `db` / `models`.

## Modules

<!-- reignit:modules:start -->

### cli (`src/reignit/cli.py`)

User-facing commands: `init`, `refresh`, `serve`, `show`.

Key paths:
- `src/reignit/cli.py`

### server (`src/reignit/server.py`)

FastAPI app. Compatible probe on `GET /` (`Ollama is running`), health, and a catch-all proxy to Ollama. Injects the wiki on chat/generate paths.

Key paths:
- `src/reignit/server.py`

### inject (`src/reignit/inject.py`)

Builds the wiki system block and splices it into OpenAI messages, Ollama chat, and generate/completion payloads. Replaces a stale `BEGIN REIGNIT WIKI` block if the client already sent one.

Key paths:
- `src/reignit/inject.py`

### wiki (`src/reignit/wiki.py`)

Load, render, and refresh the two wiki files. History is newest-first.

Key paths:
- `src/reignit/wiki.py`
- `src/reignit/init_project.py`
- `src/reignit/scan.py`

### config (`src/reignit/config.py`)

`REIGNIT_*` settings: host, port, Ollama URL, default workspace.

Key paths:
- `src/reignit/config.py`
- `src/reignit/constants.py`

### tests (`tests/`)

Unit tests for injection, init/refresh, and the proxy.

Key paths:
- `tests/test_inject.py`
- `tests/test_init.py`
- `tests/test_server.py`

<!-- reignit:modules:end -->
