"""Web vulnerability scanner module for PenKit."""

from typing import Any, Dict, List, Optional

from penkit.core.exceptions import ModuleError
from penkit.core.plugin import PenKitPlugin
from penkit.integrations.sqlmap_integration import SQLMapIntegration


class WebScannerPlugin(PenKitPlugin):
    """Web vulnerability scanner plugin for PenKit."""

    name = "web_scanner"
    description = "Scan web applications for vulnerabilities"
    version = "0.1.0"
    author = "PenKit Team"

    def __init__(self) -> None:
        """Initialize the web scanner plugin."""
        super().__init__()
        self.options = {
            "target_url": "",
            "data": "",  # POST data
            "cookie": "",
            "user_agent": "PenKit Web Scanner",
            "scan_level": "1",  # 1-5
            "risk_level": "1",  # 1-3
            "forms": True,  # Scan forms
            "crawl_depth": "0",  # 0 = disabled
            "threads": "1",
            "timeout": 1800,  # 30 minutes
            "scan_type": "quick",  # quick, thorough
        }

        # Initialize SQLmap integration
        self.sqlmap = SQLMapIntegration()

    def setup(self) -> None:
        """Set up the plugin."""
        # Check if SQLmap is available
        if not self.sqlmap.binary_path and not self.sqlmap.use_container:
            print(
                "Warning: SQLmap is not available. Web scanning functionality will be limited."
            )

    def run(self) -> Dict[str, Any]:
        """Run the web vulnerability scanner.

        Returns:
            Scan results

        Raises:
            ModuleError: If the scan fails
        """
        target_url = self.options.get("target_url")
        if not target_url:
            raise ModuleError("Target URL must be specified")

        # Build scan options from module options
        scan_options = {
            "data": self.options.get("data"),
            "cookie": self.options.get("cookie"),
            "user_agent": self.options.get("user_agent"),
            "level": self.options.get("scan_level"),
            "risk": self.options.get("risk_level"),
            "forms": self.options.get("forms"),
            "timeout": self.options.get("timeout"),
        }

        # Add crawl depth if enabled
        crawl_depth = self.options.get("crawl_depth")
        if crawl_depth and int(crawl_depth) > 0:
            scan_options["crawl"] = crawl_depth

        # Add threading if more than 1
        threads = self.options.get("threads")
        if threads and int(threads) > 1:
            scan_options["threads"] = threads

        # Remove empty options
        scan_options = {k: v for k, v in scan_options.items() if v}

        # Run the scan based on scan type
        try:
            scan_type = self.options.get("scan_type", "quick")
            
            if scan_type == "thorough":
                results = self.sqlmap.thorough_scan(target_url, **scan_options)
            else:  # Default to quick scan
                results = self.sqlmap.quick_scan(target_url)
                
            return self._format_results(results)
        except Exception as e:
            raise ModuleError(f"Web vulnerability scan failed: {str(e)}")

    def _format_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Format scan results.

        Args:
            results: Raw scan results

        Returns:
            Formatted results
        """
        formatted = {
            "target_url": self.options.get("target_url"),
            "scan_type": self.options.get("scan_type"),
            "vulnerabilities": results.get("vulnerabilities", []),
            "summary": results.get("summary", {}),
        }
        
        # Add vulnerability count
        formatted["vulnerability_count"] = len(formatted["vulnerabilities"])
        
        # Add vulnerability types summary
        vuln_types = {}
        for vuln in formatted["vulnerabilities"]:
            vuln_type = vuln.get("type", "unknown")
            vuln_types[vuln_type] = vuln_types.get(vuln_type, 0) + 1
            
        formatted["vulnerability_types"] = vuln_types
        
        return formatted
