from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reignit.constants import DEFAULT_HOST, DEFAULT_OLLAMA, DEFAULT_PORT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REIGNIT_",
        env_file=".env",
        extra="ignore",
    )

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    ollama: str = DEFAULT_OLLAMA
    workspace: Path | None = Field(
        default=None,
        description="Default project whose wiki is injected when a request does not name one.",
    )

    def ollama_base(self) -> str:
        return self.ollama.rstrip("/")
