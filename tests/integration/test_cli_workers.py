
import pytest
from click.testing import CliRunner
from snackbase.cli import cli
from unittest.mock import patch

def test_serve_invalid_workers_sqlite():
    """Verify CLI fails when --workers > 1 is used with SQLite."""
    runner = CliRunner()
    
    # Mock settings to use SQLite
    with patch("snackbase.cli.get_settings") as mock_get_settings:
        from unittest.mock import MagicMock
        mock_settings = MagicMock()
        mock_settings.database_url = "sqlite+aiosqlite:///./sb_data/snackbase.db"
        mock_settings.host = "0.0.0.0"
        mock_settings.port = 8000
        mock_settings.workers = 1
        mock_settings.is_development = True
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings
        
        # Test with --workers 2
        result = runner.invoke(cli, ["serve", "--workers", "2"])
        
        assert result.exit_code == 1
        assert "Error: SQLite does not support multiple worker processes" in result.output

def test_serve_valid_workers_sqlite():
    """Verify CLI succeeds (or at least passes validation) with --workers 1 and SQLite."""
    runner = CliRunner()
    
    # Mock settings to use SQLite
    # We mock uvicorn.run to prevent the actual server from starting
    with patch("snackbase.cli.get_settings") as mock_get_settings, \
         patch("uvicorn.run") as mock_run:
        from unittest.mock import MagicMock
        mock_settings = MagicMock()
        mock_settings.database_url = "sqlite+aiosqlite:///./sb_data/snackbase.db"
        mock_settings.host = "0.0.0.0"
        mock_settings.port = 8000
        mock_settings.workers = 1
        mock_settings.is_development = True
        mock_settings.log_level = "INFO"
        mock_settings.environment = "development"
        mock_get_settings.return_value = mock_settings
        
        # Test with default workers (1)
        result = runner.invoke(cli, ["serve"])
        
        # It should reach uvicorn.run
        assert result.exit_code == 0
        mock_run.assert_called_once()
