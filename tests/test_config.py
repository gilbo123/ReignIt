from pathlib import Path

import pytest

from reignit.config import load_settings


def test_load_settings_from_repo_root() -> None:
    settings = load_settings()
    assert settings.host == "0.0.0.0"
    assert settings.port == 11444
    assert settings.ollama == "http://192.168.1.200:11434"
    assert settings.public_url == "http://192.168.1.200:11444"
    assert settings.workspace is None


def test_load_settings_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="reignit.toml"):
        load_settings()
