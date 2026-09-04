import pytest

from reignit.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        host="127.0.0.1",
        port=11444,
        ollama="http://127.0.0.1:11434",
        public_url="http://127.0.0.1:11444",
    )
