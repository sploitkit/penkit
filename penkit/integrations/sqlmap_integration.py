"""SQLmap integration for PenKit."""

import json
import os
import re
import tempfile
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from penkit.core.exceptions import IntegrationError, OutputParsingError
from penkit.core.models import Severity
from penkit.integrations.base import CommandBuilder, ToolIntegration

logger = logging.getLogger(__name__)

class SQLMapIntegration(ToolIntegration):
    """Integration for the SQLmap SQL injection scanner."""

    name = "sqlmap"
    description = "Automatic SQL injection detection and exploitation"
    binary_name = "sqlmap"
    version_args = ["--version"]
    default_args = ["--batch"]  # Non-interactive mode
    container_image = "vulnerables/sqlmap-python3"
    container_options = []
    version_pattern = re.compile(r"sqlmap (\d+\.\d+(?:\.\d+)?)")

    def __init__(self) -> None:
        """Initialize the SQLmap integration."""
        super().__init__()
        # Default to not supporting JSON output
        self._supports_json_output = False
        
        # Only check capabilities if we found SQLMap
        if self.binary_path:
            self._check_capabilities()
    
    def _check_capabilities(self) -> None:
        """Check SQLMap capabilities by testing help output."""
        try:
            # Check if --json-output is in the help text
            result = self.run("--help")
            if result.stdout and "--json-output" in result.stdout:
                self._supports_json_output = True
                logger.debug("SQLMap supports JSON output")
            else:
                logger.debug("SQLMap does not support JSON output flag")
        except Exception as e:
            logger.warning(f"Error checking SQLMap capabilities: {e}")

    def _get_version(self) -> str:
        """Get the SQLmap version.

        Returns:
            Version string

        Raises:
            IntegrationError: If version cannot be determined
        """
        if not self.binary_path:
            if self.use_container and self.container_image:
                # For container-based tools, return a placeholder version
                return "container:" + self.container_image
            raise IntegrationError("SQLmap binary not found")

        result = super()._get_version()
        match = self.version_pattern.search(result)
        if match:
            return match.group(1)

        return result

    def scan(self, target_url: str, *args: str, **options: Any) -> Dict[str, Any]:
        """Run a SQLmap scan against a target URL.

        Args:
            target_url: Target URL to scan
            *args: Additional SQLmap arguments
            **options: Additional options
                - data: POST data to include
                - cookie: Cookies to use
                - headers: Custom headers
                - user_agent: User agent to use
                - level: Detection level (1-5)
                - risk: Risk level (1-3)
                - dbms: Target DBMS
                - forms: Automatically test forms
                - crawl: Crawl the website with specified depth
                - threads: Number of concurrent threads
                - timeout: Timeout in seconds (default: 600)
                - output_dir: Directory to save scan results

        Returns:
            Scan results

        Raises:
            IntegrationError: If the scan fails
        """
        if not target_url:
            raise IntegrationError("Target URL is required for SQLmap scan")

        cmd_builder = CommandBuilder([self.binary_name if self.binary_path else "sqlmap"])

        # Add target URL
        cmd_builder.add_flag("-u", target_url)
        
        # Add batch mode for non-interactive execution
        cmd_builder.add_flag("--batch")
        
        # Create a temporary directory for output if not specified
        output_dir = options.get("output_dir")
        if not output_dir:
            # Create directory in user's home folder to ensure write permissions
            output_dir = os.path.join(os.path.expanduser("~"), ".penkit", "sqlmap_output")
            os.makedirs(output_dir, exist_ok=True)
        
        # Add output directory flag
        cmd_builder.add_flag("--output-dir", output_dir)
        
        # Only add JSON output flag if supported
        if self._supports_json_output:
            results_json = os.path.join(output_dir, "results.json")
            cmd_builder.add_flag("--json-output", results_json)
        
        # Add POST data if provided
        if "data" in options and options["data"]:
            cmd_builder.add_flag("--data", options["data"])
            
        # Add cookie if provided
        if "cookie" in options and options["cookie"]:
            cmd_builder.add_flag("--cookie", options["cookie"])
            
        # Add custom headers if provided
        if "headers" in options and options["headers"]:
            for header, value in options["headers"].items():
                cmd_builder.add_flag("-H", f"{header}: {value}")
                
        # Add user agent if provided
        if "user_agent" in options and options["user_agent"]:
            cmd_builder.add_flag("--user-agent", options["user_agent"])
            
        # Add detection level if provided
        if "level" in options and options["level"]:
            cmd_builder.add_flag("--level", options["level"])
            
        # Add risk level if provided
        if "risk" in options and options["risk"]:
            cmd_builder.add_flag("--risk", options["risk"])
            
        # Add target DBMS if provided
        if "dbms" in options and options["dbms"]:
            cmd_builder.add_flag("--dbms", options["dbms"])
            
        # Add form testing if enabled
        if options.get("forms", False):
            cmd_builder.add_flag("--forms")
            
        # Add crawling if enabled
        if "crawl" in options and options["crawl"]:
            cmd_builder.add_flag("--crawl", options["crawl"])
            
        # Add threading if specified
        if "threads" in options and options["threads"]:
            cmd_builder.add_flag("--threads", options["threads"])
        
        # Add additional arguments
        for arg in args:
            cmd_builder.add_arg(arg)

        # Extract timeout from options if present
        timeout = options.get("timeout", 600)  # Default: 10 minutes
        
        # Log the full command for debugging
        logger.debug(f"Running SQLMap command: {cmd_builder.build()}")

        # Run the scan
        result = self.run(*cmd_builder.build()[1:], timeout=timeout)

        # Check for errors
        if result.status == "error":
            raise IntegrationError(f"SQLmap scan failed: {result.stderr}")

        if result.status == "timeout":
            raise IntegrationError(f"SQLmap scan timed out after {timeout} seconds")

        if result.status == "parse_error":
            raise OutputParsingError("Failed to parse SQLmap output")

        # Try to read JSON results if available
        if self._supports_json_output:
            results_json = os.path.join(output_dir, "results.json")
            if os.path.exists(results_json):
                try:
                    with open(results_json, 'r') as f:
                        json_data = json.load(f)
                        parsed_result = self._process_json_output(json_data)
                        return parsed_result
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Error reading JSON results: {e}")
        
        # Fall back to parsed output from stdout
        if result.parsed_result:
            return result.parsed_result
        
        # If all else fails, parse stdout directly
        return self._parse_text_output(result.stdout or "")

    def parse_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse SQLmap output.

        Args:
            stdout: Standard output from SQLmap
            stderr: Standard error from SQLmap

        Returns:
            Parsed output as a dictionary

        Raises:
            OutputParsingError: If parsing fails
        """
        if not stdout and not stderr:
            raise OutputParsingError("No output from SQLmap")

        result = {
            "vulnerabilities": [],
            "summary": {},
            "raw_output": stdout,
        }

        # Try to find JSON in the output
        json_match = re.search(r'({.*"data".*})', stdout, re.DOTALL)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                processed = self._process_json_output(json_data)
                result.update(processed)
                return result
            except json.JSONDecodeError:
                pass  # Fall back to text parsing

        # Try to parse stdout as text
        parsed_result = self._parse_text_output(stdout)
        result.update(parsed_result)
        
        return result

    def _process_json_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON output from SQLmap.

        Args:
            data: JSON data from SQLmap

        Returns:
            Processed data as a dictionary
        """
        result = {
            "vulnerabilities": [],
            "summary": {},
        }
        
        # Extract vulnerabilities
        if "data" in data and "vulnerable" in data["data"]:
            for target_url, vulnerabilities in data["data"]["vulnerable"].items():
                for vuln_type, details in vulnerabilities.items():
                    # Create vulnerability object
                    vulnerability = {
                        "title": f"SQL Injection ({vuln_type})",
                        "description": f"SQL Injection vulnerability found in {target_url}",
                        "severity": Severity.HIGH,  # SQL injection is typically high severity
                        "url": target_url,
                        "type": vuln_type,
                        "details": details,
                    }
                    result["vulnerabilities"].append(vulnerability)
        
        # Extract summary
        if "data" in data and "stats" in data["data"]:
            result["summary"] = data["data"]["stats"]
            
        return result

    def _parse_text_output(self, output: str) -> Dict[str, Any]:
        """Parse text output from SQLmap.

        Args:
            output: Text output from SQLmap

        Returns:
            Parsed data as a dictionary
        """
        result = {
            "vulnerabilities": [],
            "summary": {
                "scan_time": "",
                "vulnerabilities_found": 0,
                "scan_completed": False,
            },
        }
        
        # Log the first part of output for debugging
        if output:
            logger.debug(f"Parsing SQLMap output: {output[:200]}...")
        
        # Extract target URL
        target_url = None
        url_pattern = re.compile(r"URL: (https?://\S+)")
        url_match = url_pattern.search(output)
        if url_match:
            target_url = url_match.group(1)
            logger.debug(f"Found target URL: {target_url}")
        
        # Check for vulnerabilities
        vuln_pattern = re.compile(r"(?:parameter|Parameter|GET parameter|POST parameter) '([^']+)'.+(?:is vulnerable to|vulnerable to) '?([^']+)'?")
        for match in vuln_pattern.finditer(output):
            param, vuln_type = match.groups()
            
            vulnerability = {
                "title": f"SQL Injection ({vuln_type})",
                "description": f"SQL Injection vulnerability found in parameter '{param}'",
                "severity": Severity.HIGH,
                "url": target_url if target_url else "Unknown",
                "parameter": param,
                "type": vuln_type,
            }
            result["vulnerabilities"].append(vulnerability)
        
        # Extract scan time
        time_pattern = re.compile(r"scan spent ([0-9:]+)")
        time_match = time_pattern.search(output)
        if time_match:
            result["summary"]["scan_time"] = time_match.group(1)
        
        # Update summary
        result["summary"]["vulnerabilities_found"] = len(result["vulnerabilities"])
        result["summary"]["scan_completed"] = "scan completed" in output.lower()
        
        return result

    def quick_scan(self, target_url: str) -> Dict[str, Any]:
        """Perform a quick scan of the target URL.

        Args:
            target_url: Target URL to scan

        Returns:
            Scan results
        """
        return self.scan(
            target_url,
            level="1",
            risk="1",
        )

    def thorough_scan(self, target_url: str, **options: Any) -> Dict[str, Any]:
        """Perform a thorough scan of the target URL.

        Args:
            target_url: Target URL to scan
            **options: Additional options

        Returns:
            Scan results
        """
        scan_options = {
            "level": "3",
            "risk": "2",
            "forms": True,
        }
        scan_options.update(options)
        
        return self.scan(target_url, **scan_options)

    def get_vulnerability_summary(self, scan_result: Dict[str, Any]) -> Dict[str, int]:
        """Get a summary of vulnerabilities from scan results.

        Args:
            scan_result: Scan results

        Returns:
            Dictionary with vulnerability counts by type
        """
        summary = {}
        
        for vuln in scan_result.get("vulnerabilities", []):
            vuln_type = vuln.get("type", "unknown")
            summary[vuln_type] = summary.get(vuln_type, 0) + 1
            
        return summary