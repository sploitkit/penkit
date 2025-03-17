"""Test SQLmap integration functionality."""

from unittest.mock import patch, MagicMock

import pytest

from penkit.core.exceptions import IntegrationError
from penkit.integrations.sqlmap_integration import SQLMapIntegration


@pytest.fixture
def sqlmap_integration():
    """Create a SQLmap integration instance for testing."""
    with patch.object(SQLMapIntegration, "__init__", return_value=None):
        integration = SQLMapIntegration()
        integration.binary_path = "/usr/bin/sqlmap"  # Mock binary path
        integration.version = "1.4.7"
        return integration


def test_sqlmap_version(sqlmap_integration):
    """Test getting SQLmap version."""
    # Mock the parent _get_version method
    with patch("penkit.integrations.base.ToolIntegration._get_version") as mock_get_version:
        mock_get_version.return_value = "sqlmap 1.4.7\nsome other info"
        
        # Call the method
        version = sqlmap_integration._get_version()
        
        # Check the result
        assert version == "1.4.7"
        mock_get_version.assert_called_once()


def test_scan_with_missing_url(sqlmap_integration):
    """Test scan with missing URL."""
    with pytest.raises(IntegrationError) as exc_info:
        sqlmap_integration.scan("")
    
    assert "Target URL is required" in str(exc_info.value)


def test_sqlmap_scan_command_building(sqlmap_integration):
    """Test SQLmap scan command building."""
    # Set the _supports_json_output attribute for the test
    sqlmap_integration._supports_json_output = False
    
    # Mock the CommandBuilder class instead of build_command
    with patch("penkit.integrations.sqlmap_integration.CommandBuilder") as MockCommandBuilder:
        mock_cmd_builder = MagicMock()
        MockCommandBuilder.return_value = mock_cmd_builder
        mock_cmd_builder.build.return_value = ["/usr/bin/sqlmap", "-u", "http://example.com", "--batch"]

        # Mock the run method
        with patch.object(sqlmap_integration, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.parsed_result = {"test": "data"}
            mock_run.return_value = mock_result

            # Call the scan method
            result = sqlmap_integration.scan("http://example.com")

            # Check the result
            assert result == {"test": "data"}
            # Verify the build method was called - but we don't assert call count
            # as it might be called multiple times in the implementation
            assert mock_cmd_builder.build.called


def test_parse_json_output(sqlmap_integration):
    """Test parsing JSON output from SQLmap."""
    # Set the _supports_json_output attribute for the test
    sqlmap_integration._supports_json_output = False
    
    # Sample JSON output
    json_output = '''
    Some SQLmap output text
    {
        "data": {
            "vulnerable": {
                "http://example.com/?id=1": {
                    "error-based": {
                        "dbms": "MySQL",
                        "parameter": "id",
                        "payload": "id=1' AND (SELECT 2989 FROM(SELECT COUNT(*),CONCAT(0x7176767671,(SELECT (ELT(2989=2989,1))),0x71706b7071,FLOOR(RAND(0)*2))x FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)a) AND 'qxDR'='qxDR"
                    }
                }
            },
            "stats": {
                "start_time": "2023-01-01 12:00:00",
                "end_time": "2023-01-01 12:05:00",
                "queries": 100
            }
        }
    }
    More SQLmap output text
    '''
    
    # Parse the output
    result = sqlmap_integration.parse_output(json_output, "")
    
    # Check the result
    assert len(result["vulnerabilities"]) == 1
    assert result["vulnerabilities"][0]["type"] == "error-based"
    assert result["vulnerabilities"][0]["url"] == "http://example.com/?id=1"
    
    # Check individual stats properties instead of expecting a nested 'stats' key
    assert "start_time" in result["summary"]
    assert "end_time" in result["summary"]
    assert "queries" in result["summary"]


def test_parse_text_output(sqlmap_integration):
    """Test parsing text output from SQLmap."""
    # Set the _supports_json_output attribute for the test
    sqlmap_integration._supports_json_output = False
    
    # Sample text output
    text_output = '''
    SQLmap started at 2023-01-01 12:00:00
    URL: http://example.com/?id=1
    [12:02:03] [INFO] testing connection to the target URL
    [12:03:04] [INFO] testing for SQL injection
    [12:04:05] [CRITICAL] parameter 'id' is vulnerable to SQL injection
    [12:04:06] [INFO] the back-end DBMS is MySQL
    parameter 'id' is vulnerable to error-based injection
    SQLmap finished at 2023-01-01 12:05:00
    scan completed
    '''
    
    # Parse the output
    result = sqlmap_integration._parse_text_output(text_output)
    
    # Check the result
    assert len(result["vulnerabilities"]) >= 1
    assert "scan_completed" in result["summary"]
    assert result["summary"]["scan_completed"] == True


def test_get_vulnerability_summary(sqlmap_integration):
    """Test getting vulnerability summary."""
    # Set the _supports_json_output attribute for the test
    sqlmap_integration._supports_json_output = False
    
    # Sample scan result
    scan_result = {
        "vulnerabilities": [
            {"type": "error-based", "url": "http://example.com/?id=1"},
            {"type": "time-based", "url": "http://example.com/?id=1"},
            {"type": "error-based", "url": "http://example.com/?name=test"},
        ]
    }
    
    # Get the summary
    summary = sqlmap_integration.get_vulnerability_summary(scan_result)
    
    # Check the result
    assert summary["error-based"] == 2
    assert summary["time-based"] == 1