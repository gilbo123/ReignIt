from pathlib import Path

from reignit.init_project import init_wiki, is_existing_project, refresh_wiki
from reignit.wiki import load_wiki


def test_init_new_project(tmp_path: Path) -> None:
    empty = tmp_path / "blank"
    actions = init_wiki(empty)
    assert actions["wiki/functionality.md"] == "created"
    assert actions["wiki/history.md"] == "created"
    wiki = load_wiki(empty)
    assert wiki.present
    assert "Functionality" in wiki.functionality
    assert "Wiki initialized" in wiki.history
    assert "Empty or new project" in wiki.history


def test_init_existing_project_scans_modules(tmp_path: Path) -> None:
    (tmp_path / "src" / "ui").mkdir(parents=True)
    (tmp_path / "src" / "ui" / "App.tsx").write_text("export const App = () => null;\n")
    (tmp_path / "README.md").write_text("# Demo\n\nA sample application.\n")
    actions = init_wiki(tmp_path)
    assert actions["wiki/functionality.md"] == "created"
    wiki = load_wiki(tmp_path)
    assert "A sample application." in wiki.functionality
    assert "src/ui/App.tsx" in wiki.functionality
    assert "Existing project scanned" in wiki.history


def test_init_does_not_overwrite(tmp_path: Path) -> None:
    init_wiki(tmp_path)
    (tmp_path / "wiki" / "functionality.md").write_text("# custom\n")
    actions = init_wiki(tmp_path)
    assert actions["wiki/functionality.md"] == "exists"
    assert (tmp_path / "wiki" / "functionality.md").read_text() == "# custom\n"


def test_refresh_keeps_overview(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n")
    init_wiki(tmp_path)
    func = tmp_path / "wiki" / "functionality.md"
    text = func.read_text()
    start = text.find("## Overview")
    end = text.find("## How to target")
    func.write_text(text[:start] + "## Overview\n\nCustom overview lives here\n\n" + text[end:])
    (tmp_path / "src" / "api.py").write_text("def run(): ...\n")
    refresh_wiki(tmp_path)
    updated = func.read_text()
    assert "Custom overview lives here" in updated
    assert "src/api.py" in updated


def test_empty_dir_is_not_existing(tmp_path: Path) -> None:
    assert is_existing_project(tmp_path) is False
    (tmp_path / ".git").mkdir()
    assert is_existing_project(tmp_path) is False
    (tmp_path / "main.py").write_text("x = 1\n")
    assert is_existing_project(tmp_path) is True
