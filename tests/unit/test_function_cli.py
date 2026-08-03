"""Contract tests for functions CLI registration."""

from click.testing import CliRunner

from snackbase.cli import cli


def test_functions_group_registered() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["functions", "--help"])
    assert result.exit_code == 0
    assert "deploy" in result.output
    assert "list" in result.output
    assert "logs" in result.output
    assert "serve" in result.output


def test_functions_list_requires_token() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["functions", "list"], env={"SNACKBASE_TOKEN": ""})
    # Click fails when required option missing
    assert result.exit_code != 0
