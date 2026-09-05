from __future__ import annotations

from pathlib import Path

import typer

from reignit import CURRENT_FILE, FUNCTIONALITY_FILE, HISTORY_FILE, WIKI_DIR, __version__
from reignit.config import load_settings
from reignit.init_project import ensure_wiki, init_wiki, refresh_wiki
from reignit.wiki import load_wiki

app = typer.Typer(
    name="reignit",
    help="Wiki-backed harness for local models running on maxed-out hardware.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    return


@app.command()
def reinit(
    path: Path = typer.Argument(
        Path("."),
        exists=False,
        file_okay=False,
        resolve_path=True,
        help="Project directory on the server.",
    ),
) -> None:
    """Regenerate wiki/functionality.md, wiki/current.md, and wiki/history.md."""
    actions = init_wiki(path, force=True)
    typer.echo(f"ReignIt wiki reinitialized in {path}")
    for relative, action in actions.items():
        typer.echo(f"  {action:8} {relative}")


@app.command("refresh")
def refresh(
    path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        resolve_path=True,
        help="Project directory whose module map should be rescanned.",
    ),
) -> None:
    """Rescan the tree and refresh the module map. Keeps the written overview."""
    relative = refresh_wiki(path)
    typer.echo(f"Refreshed module map in {relative}")


@app.command()
def serve() -> None:
    """Serve the harness. All settings come from reignit.toml in the repo root."""
    try:
        settings = load_settings()
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("Config:  reignit.toml")
    typer.echo(f"Ollama:  {settings.ollama_base()}")
    typer.echo(f"Listen:  {settings.host}:{settings.port}")
    typer.echo(f"Clients: {settings.public_url}")
    typer.echo("Wiki:    auto-seeded on first request; pass ?workspace=/path/on/server")
    if settings.workspace:
        ensure_wiki(settings.workspace)
        wiki = load_wiki(settings.workspace)
        typer.echo(f"Fallback wiki: {settings.workspace / WIKI_DIR} ({'ok' if wiki.present else 'missing'})")

    from reignit.server import run

    run(settings)


@app.command()
def show(
    path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        resolve_path=True,
        help="Project directory.",
    ),
) -> None:
    """Print the wiki that would be injected (seeds defaults if missing)."""
    ensure_wiki(path)
    wiki = load_wiki(path)
    typer.echo(f"# {WIKI_DIR}/{CURRENT_FILE}\n")
    typer.echo(wiki.current)
    typer.echo(f"\n# {WIKI_DIR}/{FUNCTIONALITY_FILE}\n")
    typer.echo(wiki.functionality)
    typer.echo(f"\n# {WIKI_DIR}/{HISTORY_FILE}\n")
    typer.echo(wiki.history)
