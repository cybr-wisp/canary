import asyncio
import re

import httpx
import typer
from rich.console import Console

from app.github.client import GitHubClient
from app.services.pr_analysis import analyze_pull_request
from app.terminal.presentation import render_analysis


app = typer.Typer(
    name="canary",
    help="🐤 Behavioral regression detection for GitHub pull requests.",
    no_args_is_help=True,
)

console = Console()


PR_URL_PATTERN = re.compile(
    r"^https?://github\.com/"
    r"(?P<owner>[^/]+)/"
    r"(?P<repo>[^/]+)/pull/"
    r"(?P<number>\d+)/?$"
)


def parse_pull_request_url(
    url: str,
) -> tuple[str, int]:
    """
    Parse a GitHub pull request URL.

    Example:
        https://github.com/cybr-wisp/canary-testbed/pull/1
    """

    match = PR_URL_PATTERN.match(url.strip())

    if not match:
        raise ValueError(
            "Expected a GitHub pull request URL like "
            "https://github.com/owner/repository/pull/123"
        )

    repository = (
        f"{match.group('owner')}/"
        f"{match.group('repo')}"
    )

    pull_number = int(match.group("number"))

    return repository, pull_number


async def inspect_pull_request(
    url: str,
) -> None:
    """
    Fetch and analyze one GitHub pull request.
    """

    try:
        repository, pull_number = parse_pull_request_url(url)

    except ValueError as exc:
        console.print()
        console.print(
            "[bold red]✗ Invalid pull request URL[/bold red]"
        )
        console.print(
            f"[dim]{exc}[/dim]"
        )
        console.print()

        raise typer.Exit(code=2) from exc

    github = GitHubClient()

    try:
        with console.status(
            "[bold yellow]🐤 Canary is inspecting the pull request..."
        ):
            installation_id = (
                await github.get_repository_installation_id(
                    repository
                )
            )

            result = await analyze_pull_request(
                repository=repository,
                pull_number=pull_number,
                installation_id=installation_id,
            )

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code

        console.print()

        if status_code == 404:
            console.print(
                "[bold red]"
                "✗ Canary cannot access this repository."
                "[/bold red]"
            )
            console.print(
                "[dim]"
                "Make sure the Canary GitHub App is installed "
                "on the repository."
                "[/dim]"
            )

        else:
            console.print(
                "[bold red]"
                f"✗ GitHub API request failed ({status_code})."
                "[/bold red]"
            )

        console.print()

        raise typer.Exit(code=1) from exc

    except httpx.RequestError as exc:
        console.print()
        console.print(
            "[bold red]✗ Could not connect to GitHub.[/bold red]"
        )
        console.print(
            f"[dim]{exc}[/dim]"
        )
        console.print()

        raise typer.Exit(code=1) from exc

    render_analysis(
        console,
        repository=repository,
        pull_number=pull_number,
        result=result,
    )


@app.command()
def inspect(
    url: str = typer.Argument(
        ...,
        help="GitHub pull request URL to inspect.",
    ),
) -> None:
    """
    Analyze a GitHub pull request for behavioral regression signals.
    """

    asyncio.run(
        inspect_pull_request(url)
    )


@app.callback()
def main() -> None:
    """Canary command-line interface."""


if __name__ == "__main__":
    app()