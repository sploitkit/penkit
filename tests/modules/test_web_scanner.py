"""Test web scanner module functionality."""

from unittest.mock import patch, MagicMock

import pytest

from penkit.core.exceptions import ModuleError
from penkit.modules.web_scanner import WebScannerPlugin


@pytest.fixture
def web_scanner():
    """Create a web scanner plugin instance for testing."""
    with patch("penkit.integrations.sqlmap_integration.SQLMapIntegration") as MockSQLMap:
        # Configure the mock
        mock_sqlmap = MagicMock()
        MockSQLMap.return_value = mock_sqlmap
        
        # Create the plugin
        plugin = WebScannerPlugin()
        
        # Set the mock sqlmap
        plugin.sqlmap = mock_sqlmap
        
        return plugin


def test_web_scanner_initialization(web_scanner):
    """Test web scanner initialization."""
    # Check if options are correctly initialized
    assert "target_url" in web_scanner.options
    assert "scan_type" in web_scanner.options
    assert web_scanner.options["scan_type"] == "quick"


def test_run_without_target_url(web_scanner):
    """Test running without a target URL."""
    with pytest.raises(ModuleError) as exc_info:
        web_scanner.run()
    
    assert "Target URL must be specified" in str(exc_info.value)


def test_run_quick_scan(web_scanner):
    """Test running a quick scan."""
    # Set options
    web_scanner.options["target_url"] = "http://example.com"
    web_scanner.options["scan_type"] = "quick"
    
    # Mock SQLmap quick_scan
    mock_result = {
        "vulnerabilities": [
            {"type": "error-based", "url": "http://example.com/?id=1"}
        ],
        "summary": {"scan_time": "00:05:00"}
    }
    web_scanner.sqlmap.quick_scan.return_value = mock_result
    
    # Run the scan
    result = web_scanner.run()
    
    # Check the result
    assert result["target_url"] == "http://example.com"
    assert result["scan_type"] == "quick"
    assert len(result["vulnerabilities"]) == 1
    assert result["vulnerability_count"] == 1
    assert "error-based" in result["vulnerability_types"]
    
    # Verify SQLmap was called correctly
    web_scanner.sqlmap.quick_scan.assert_called_once_with("http://example.com")


def test_run_thorough_scan(web_scanner):
    """Test running a thorough scan."""
    # Set options
    web_scanner.options["target_url"] = "http://example.com"
    web_scanner.options["scan_type"] = "thorough"
    web_scanner.options["scan_level"] = "3"
    web_scanner.options["forms"] = True
    
    # Mock SQLmap thorough_scan
    mock_result = {
        "vulnerabilities": [
            {"type": "error-based", "url": "http://example.com/?id=1"},
            {"type": "time-based", "url": "http://example.com/?id=1"}
        ],
        "summary": {"scan_time": "00:15:00"}
    }
    web_scanner.sqlmap.thorough_scan.return_value = mock_result
    
    # Run the scan
    result = web_scanner.run()
    
    # Check the result
    assert result["target_url"] == "http://example.com"
    assert result["scan_type"] == "thorough"
    assert len(result["vulnerabilities"]) == 2
    assert result["vulnerability_count"] == 2
    assert result["vulnerability_types"]["error-based"] == 1
    assert result["vulnerability_types"]["time-based"] == 1
    
    # Verify SQLmap was called correctly with the expected options
    web_scanner.sqlmap.thorough_scan.assert_called_once()
    args, kwargs = web_scanner.sqlmap.thorough_scan.call_args
    assert args[0] == "http://example.com"
    assert kwargs["level"] == "3"
    assert kwargs["forms"] == True


def test_scan_failure_handling(web_scanner):
    """Test handling of scan failures."""
    # Set options
    web_scanner.options["target_url"] = "http://example.com"
    
    # Mock SQLmap quick_scan to raise an exception
    web_scanner.sqlmap.quick_scan.side_effect = Exception("Connection error")
    
    # Run the scan and expect an error
    with pytest.raises(ModuleError) as exc_info:
        web_scanner.run()
    
    assert "Web vulnerability scan failed" in str(exc_info.value)
    assert "Connection error" in str(exc_info.value)
