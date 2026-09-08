from pathlib import Path

import pytest

from reignit.config import load_settings


def test_load_settings_from_repo_root() -> None:
    settings = load_settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 11444
    assert settings.ollama == "http://192.168.1.200:11434"
    assert settings.public_url == "http://127.0.0.1:11444"
    assert settings.api_key is None


def test_load_settings_accepts_ollama_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "reignit.toml"
    config.write_text(
        '\n'.join(
            [
                'host = "127.0.0.1"',
                'port = 11444',
                'public_url = "http://127.0.0.1:11444"',
                'ollama = "http://10.0.0.5:11434"',
                'api_key = "sk-secret"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    settings = load_settings()
    assert settings.ollama == "http://10.0.0.5:11434"
    assert settings.api_key == "sk-secret"


def test_load_settings_requires_upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "reignit.toml"
    config.write_text(
        '\n'.join(
            [
                'host = "127.0.0.1"',
                'port = 11444',
                'public_url = "http://127.0.0.1:11444"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="upstream"):
        load_settings()


def test_load_settings_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="reignit.toml"):
        load_settings()
