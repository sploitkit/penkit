"""Nmap integration for PenKit."""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from penkit.core.models import Host, HostStatus, Port
from penkit.integrations.base import CommandBuilder, ToolIntegration


class NmapIntegration(ToolIntegration):
    """Integration for the Nmap security scanner."""

    name = "nmap"
    description = "Network discovery and security scanning"
    binary_name = "nmap"
    version_args = ["--version"]
    default_args = []
    container_image = "instrumentisto/nmap:latest"
    container_options = ["--net=host"]
    version_pattern = re.compile(r"Nmap version ([0-9.]+)")

    def __init__(self) -> None:
        """Initialize the Nmap integration."""
        super().__init__()

    def _get_version(self) -> str:
        """Get the Nmap version.
        
        Returns:
            Version string
            
        Raises:
            ValueError: If version cannot be determined
        """
        if not self.binary_path:
            if self.use_container and self.container_image:
                # For container-based tools, return a placeholder version
                return "container:" + self.container_image
            raise ValueError("Nmap binary not found")
        
        result = super()._get_version()
        match = self.version_pattern.search(result)
        if match:
            return match.group(1)
        
        return result

    def scan(self, target: str, *args: str, **options: Any) -> Dict[str, Any]:
        """Run an Nmap scan.
        
        Args:
            target: Target to scan (IP, hostname, CIDR)
            *args: Additional Nmap arguments
            **options: Additional options
                - ports: Port specification (e.g., "22,80,443")
                - service_detection: Enable service detection (-sV)
                - os_detection: Enable OS detection (-O)
                - script: Script to run (e.g., "default")
                - timing: Timing template (e.g., 4)
                - output_xml: Path to save XML output
            
        Returns:
            Scan results
        """
        cmd_builder = CommandBuilder([self.binary_name if self.binary_path else "nmap"])
        
        # Add output format (XML for parsing)
        cmd_builder.add_flag("-oX", "-")
        
        # Add ports if specified
        if "ports" in options:
            cmd_builder.add_flag("-p", options["ports"])
        
        # Add service detection
        if options.get("service_detection", False):
            cmd_builder.add_flag("-sV")
        
        # Add OS detection
        if options.get("os_detection", False):
            cmd_builder.add_flag("-O")
        
        # Add script
        if "script" in options:
            cmd_builder.add_flag("--script", options["script"])
        
        # Add timing template
        if "timing" in options:
            cmd_builder.add_flag("-T", options["timing"])
        
        # Add additional arguments
        for arg in args:
            cmd_builder.add_arg(arg)
        
        # Add target
        cmd_builder.add_arg(target)
        
        # Run the scan
        result = self.run(*cmd_builder.build()[1:])
        
        # Save XML output if requested
        if "output_xml" in options and result.stdout:
            with open(options["output_xml"], "w") as f:
                f.write(result.stdout)
        
        return result.parsed_result or {}

    def parse_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse Nmap XML output.
        
        Args:
            stdout: Nmap XML output
            stderr: Standard error from Nmap
            
        Returns:
            Parsed output as a dictionary
        """
        if not stdout:
            return {"error": "No output from Nmap"}
        
        try:
            return self._parse_xml(stdout)
        except ET.ParseError as e:
            return {
                "error": f"Failed to parse Nmap XML output: {e}",
                "raw_output": stdout[:200] + "..." if len(stdout) > 200 else stdout
            }

    def _parse_xml(self, xml_output: str) -> Dict[str, Any]:
        """Parse Nmap XML output.
        
        Args:
            xml_output: Nmap XML output
            
        Returns:
            Parsed output as a dictionary
            
        Raises:
            ET.ParseError: If XML parsing fails
        """
        root = ET.fromstring(xml_output)
        
        result: Dict[str, Any] = {
            "scan_info": {},
            "hosts": [],
        }
        
        # Parse scan information
        if scanner := root.find("./scanner"):
            result["scan_info"]["scanner"] = scanner.get("name", "")
            result["scan_info"]["version"] = scanner.get("version", "")
        
        if run_stats := root.find("./runstats/finished"):
            result["scan_info"]["time"] = run_stats.get("time", "")
            result["scan_info"]["elapsed"] = run_stats.get("elapsed", "")
            result["scan_info"]["exit"] = run_stats.get("exit", "")
            result["scan_info"]["summary"] = run_stats.get("summary", "")
        
        # Parse hosts
        hosts: List[Host] = []
        for host_elem in root.findall("./host"):
            host = self._parse_host(host_elem)
            if host:
                hosts.append(host)
        
        # Convert Host objects to dictionaries
        result["hosts"] = [host.dict() for host in hosts]
        
        return result

    def _parse_host(self, host_elem: ET.Element) -> Optional[Host]:
        """Parse a host element from Nmap XML.
        
        Args:
            host_elem: Host XML element
            
        Returns:
            Host object or None if parsing fails
        """
        try:
            # Get host status
            status_elem = host_elem.find("./status")
            status = HostStatus.UNKNOWN
            if status_elem is not None:
                status_str = status_elem.get("state", "")
                if status_str == "up":
                    status = HostStatus.UP
                elif status_str == "down":
                    status = HostStatus.DOWN
            
            # Get IP address
            ip_address = ""
            for addr_elem in host_elem.findall("./address"):
                if addr_elem.get("addrtype") == "ipv4":
                    ip_address = addr_elem.get("addr", "")
                    break
            
            if not ip_address:
                return None
            
            # Get hostname
            hostname = None
            for hostname_elem in host_elem.findall("./hostnames/hostname"):
                if hostname_elem.get("type") == "user":
                    hostname = hostname_elem.get("name")
                    break
            
            # Get OS information
            os_info = None
            for os_elem in host_elem.findall("./os/osmatch"):
                if os_elem.get("name"):
                    os_info = os_elem.get("name")
                    break
            
            # Get MAC address
            mac_address = None
            for addr_elem in host_elem.findall("./address"):
                if addr_elem.get("addrtype") == "mac":
                    mac_address = addr_elem.get("addr")
                    break
            
            # Get open ports
            ports: List[Port] = []
            for port_elem in host_elem.findall("./ports/port"):
                port = self._parse_port(port_elem)
                if port:
                    ports.append(port)
            
            return Host(
                ip_address=ip_address,
                hostname=hostname,
                os=os_info,
                status=status,
                mac_address=mac_address,
                open_ports=ports,
            )
        
        except Exception as e:
            print(f"Error parsing host: {e}")
            return None

    def _parse_port(self, port_elem: ET.Element) -> Optional[Port]:
        """Parse a port element from Nmap XML.
        
        Args:
            port_elem: Port XML element
            
        Returns:
            Port object or None if parsing fails
        """
        try:
            port_id = port_elem.get("portid")
            if not port_id:
                return None
            
            protocol = port_elem.get("protocol", "")
            
            # Get port state
            state_elem = port_elem.find("./state")
            state = "unknown"
            if state_elem is not None:
                state = state_elem.get("state", "unknown")
            
            # Get service information
            service_elem = port_elem.find("./service")
            service = None
            version = None
            if service_elem is not None:
                service = service_elem.get("name")
                version = service_elem.get("product", "")
                if product_version := service_elem.get("version"):
                    version += f" {product_version}"
            
            # Get script output/banner
            banner = None
            script_elem = port_elem.find("./script[@id='banner']")
            if script_elem is not None:
                banner = script_elem.get("output")
            
            return Port(
                port=int(port_id),
                protocol=protocol,
                service=service,
                version=version,
                state=state,
                banner=banner,
            )
        
        except Exception as e:
            print(f"Error parsing port: {e}")
            return None

    def quick_scan(self, target: str) -> Dict[str, Any]:
        """Perform a quick scan of the target.
        
        Args:
            target: Target to scan
            
        Returns:
            Scan results
        """
        return self.scan(target, "-T4", "-F")

    def comprehensive_scan(self, target: str) -> Dict[str, Any]:
        """Perform a comprehensive scan of the target.
        
        Args:
            target: Target to scan
            
        Returns:
            Scan results
        """
        return self.scan(
            target,
            service_detection=True,
            os_detection=True,
            script="default",
            timing=4,
        )

    def service_scan(self, target: str, ports: str) -> Dict[str, Any]:
        """Perform a service scan of specific ports.
        
        Args:
            target: Target to scan
            ports: Port specification
            
        Returns:
            Scan results
        """
        return self.scan(
            target,
            ports=ports,
            service_detection=True,
        )

    def script_scan(self, target: str, script: str, ports: Optional[str] = None) -> Dict[str, Any]:
        """Perform a script scan of the target.
        
        Args:
            target: Target to scan
            script: Script to run
            ports: Port specification (optional)
            
        Returns:
            Scan results
        """
        options: Dict[str, Any] = {
            "script": script,
        }
        
        if ports:
            options["ports"] = ports
        
        return self.scan(target, **options)

    def get_host_summary(self, scan_result: Dict[str, Any]) -> Tuple[int, int, int]:
        """Get a summary of hosts from scan results.
        
        Args:
            scan_result: Scan results
            
        Returns:
            Tuple of (total hosts, up hosts, down hosts)
        """
        hosts = scan_result.get("hosts", [])
        total = len(hosts)
        up = sum(1 for host in hosts if host.get("status") == "up")
        down = total - up
        
        return total, up, down

    def get_port_summary(self, scan_result: Dict[str, Any]) -> Dict[int, int]:
        """Get a summary of open ports from scan results.
        
        Args:
            scan_result: Scan results
            
        Returns:
            Dictionary mapping port numbers to count of hosts with that port open
        """
        port_count: Dict[int, int] = {}
        
        for host in scan_result.get("hosts", []):
            for port in host.get("open_ports", []):
                port_num = port.get("port", 0)
                if port_num > 0:
                    port_count[port_num] = port_count.get(port_num, 0) + 1
        
        return port_count
