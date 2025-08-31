"""Test CLI functionality."""

import pytest
from typer.testing import CliRunner

from skipper.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


def test_version(runner: CliRunner) -> None:
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "2.0.0-dev" in result.stdout


def test_help(runner: CliRunner) -> None:
    """Test help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Generic templated configuration management" in result.stdout


def test_compile_help(runner: CliRunner) -> None:
    """Test compile command help."""
    result = runner.invoke(app, ["compile", "--help"])
    assert result.exit_code == 0
    assert "Compile configuration for targets" in result.stdout


def test_inventory_help(runner: CliRunner) -> None:
    """Test inventory command help."""
    result = runner.invoke(app, ["inventory", "--help"])
    assert result.exit_code == 0
    assert "Show inventory for targets" in result.stdout


def test_init_help(runner: CliRunner) -> None:
    """Test init command help."""
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "Initialize a new Kapitan project" in result.stdout
