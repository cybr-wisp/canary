from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from app.cli import app, parse_pull_request_url


runner = CliRunner()


def test_parse_pull_request_url():
    repository, pull_number = parse_pull_request_url(
        "https://github.com/cybr-wisp/canary-testbed/pull/1"
    )

    assert repository == "cybr-wisp/canary-testbed"
    assert pull_number == 1


def test_parse_pull_request_url_accepts_trailing_slash():
    repository, pull_number = parse_pull_request_url(
        "https://github.com/cybr-wisp/canary-testbed/pull/42/"
    )

    assert repository == "cybr-wisp/canary-testbed"
    assert pull_number == 42


def test_parse_pull_request_url_rejects_non_pr_url():
    try:
        parse_pull_request_url(
            "https://github.com/cybr-wisp/canary-testbed"
        )
    except ValueError as exc:
        assert "Expected a GitHub pull request URL" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_cli_help_lists_inspect_command():
    result = runner.invoke(
        app,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "inspect" in result.stdout
    assert "Behavioral regression detection" in result.stdout


def test_inspect_command_dispatches_pull_request():
    url = (
        "https://github.com/"
        "cybr-wisp/canary-testbed/pull/1"
    )

    inspect_mock = AsyncMock()

    with patch(
        "app.cli.inspect_pull_request",
        new=inspect_mock,
    ):
        result = runner.invoke(
            app,
            ["inspect", url],
        )

    assert result.exit_code == 0
    inspect_mock.assert_awaited_once_with(url)