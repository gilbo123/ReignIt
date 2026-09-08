from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE = "reignit.toml"


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    ollama: str
    public_url: str
    api_key: str | None = None

    def ollama_base(self) -> str:
        return self.ollama.rstrip("/")


def load_settings() -> Settings:
    path = Path(CONFIG_FILE)
    if not path.is_file():
        raise FileNotFoundError(
            f"{CONFIG_FILE} not found. Run from the ReignIt root and create {CONFIG_FILE}."
        )

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    upstream = data.get("upstream") or data.get("ollama")
    if not upstream:
        raise ValueError(f"{CONFIG_FILE} must set upstream (or ollama) to the LLM base URL.")

    api_key = data.get("api_key")
    return Settings(
        host=str(data["host"]),
        port=int(data["port"]),
        ollama=str(upstream),
        public_url=str(data["public_url"]),
        api_key=str(api_key).strip() if api_key else None,
    )
