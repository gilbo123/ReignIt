from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from reignit import FUNCTIONALITY_FILE, HISTORY_FILE, WIKI_DIR, __version__
from reignit.config import Settings
from reignit.constants import DEFAULT_HOST, DEFAULT_OLLAMA, DEFAULT_PORT, DEFAULT_PUBLIC_URL
from reignit.init_project import init_wiki, refresh_wiki
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
def init(
    path: Path = typer.Argument(
        Path("."),
        exists=False,
        file_okay=False,
        resolve_path=True,
        help="Project directory. Created if it does not exist.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing wiki files."),
) -> None:
    """Create wiki/functionality.md and wiki/history.md in a new or existing project."""
    actions = init_wiki(path, force=force)
    typer.echo(f"ReignIt wiki in {path}")
    for relative, action in actions.items():
        typer.echo(f"  {action:8} {relative}")
    if all(action == "exists" for action in actions.values()):
        typer.echo("Already initialized. Use --force to regenerate both files.")
        return
    typer.echo(
        f"Edit {WIKI_DIR}/{FUNCTIONALITY_FILE} so the overview and module roles are accurate."
    )


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
    try:
        relative = refresh_wiki(path)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Refreshed module map in {relative}")


@app.command()
def serve(
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Bind address (default: all interfaces)."),
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Harness port."),
    ollama: str = typer.Option(DEFAULT_OLLAMA, "--ollama", help="Upstream Ollama base URL."),
    public_url: str = typer.Option(
        DEFAULT_PUBLIC_URL,
        "--public-url",
        help="URL shown in logs for clients on the LAN.",
    ),
    workspace: Optional[Path] = typer.Option(
        None,
        "--workspace",
        "-w",
        exists=True,
        file_okay=False,
        resolve_path=True,
        help="Optional fallback wiki path when a request does not name one.",
    ),
) -> None:
    """Serve an OpenAI- and Ollama-compatible endpoint that injects per-request wikis."""
    settings = Settings(
        host=host,
        port=port,
        ollama=ollama,
        public_url=public_url,
        workspace=workspace,
    )
    typer.echo(f"Ollama:  {settings.ollama_base()}")
    typer.echo(f"Listen:  {settings.host}:{settings.port}")
    typer.echo(f"Clients: {settings.public_url}")
    typer.echo("Wiki:    per request (?workspace=, X-ReignIt-Workspace, or reignit_workspace in JSON)")
    if settings.workspace:
        wiki = load_wiki(settings.workspace)
        if wiki.present:
            typer.echo(f"Fallback wiki: {settings.workspace / WIKI_DIR}")
        else:
            typer.echo(
                f"Fallback path has no wiki: {settings.workspace / WIKI_DIR}",
                err=True,
            )
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
    """Print the wiki that would be injected for this project."""
    wiki = load_wiki(path)
    if not wiki.present:
        typer.echo(f"No wiki in {path / WIKI_DIR}. Run `reignit init`.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"# {WIKI_DIR}/{FUNCTIONALITY_FILE}\n")
    typer.echo(wiki.functionality)
    typer.echo(f"\n# {WIKI_DIR}/{HISTORY_FILE}\n")
    typer.echo(wiki.history)
