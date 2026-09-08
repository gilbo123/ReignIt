from pathlib import Path

from typer.testing import CliRunner

from reignit.init_project import ensure_wiki


def test_serve_starts_without_project_path(monkeypatch) -> None:
    from reignit.cli import app

    runner = CliRunner()
    monkeypatch.setattr("reignit.server.run", lambda settings: None)
    result = runner.invoke(app, ["serve"])
    assert result.exit_code == 0
    assert "per request" in result.output


def test_ensure_wiki_on_first_request_creates_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n")
    ensure_wiki(tmp_path)
    assert (tmp_path / "wiki" / "current.md").is_file()
    assert (tmp_path / "wiki" / "functionality.md").is_file()
    assert (tmp_path / "wiki" / "history.md").is_file()
