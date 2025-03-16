"""Port scanner module for PenKit."""

from penkit.core.plugin import PenKitPlugin
from penkit.integrations.nmap_integration import NmapIntegration


class PortScannerPlugin(PenKitPlugin):
    """Port scanner plugin for PenKit."""

    name = "port_scanner"
    description = "Scan for open ports on target systems"
    version = "0.1.0"
    author = "PenKit Team"
    
    def __init__(self) -> None:
        """Initialize the port scanner plugin."""
        super().__init__()
        self.options = {
            "target": "",
            "ports": "1-1000",
            "scan_type": "tcp",
            "timing": "4",
            "output_format": "normal",
            "service_detection": True,
        }
        
        # Initialize the Nmap integration
        self.nmap = NmapIntegration()
    
    def setup(self) -> None:
        """Set up the plugin."""
        # Check if Nmap is available
        if not self.nmap.binary_path and not self.nmap.use_container:
            print("Warning: Nmap is not available. Port scanning functionality will be limited.")
    
    def run(self) -> dict:
        """Run the port scanner.
        
        Returns:
            Scan results
        
        Raises:
            ValueError: If target is not specified
        """
        target = self.options.get("target")
        if not target:
            raise ValueError("Target must be specified")
        
        ports = self.options.get("ports")
        scan_type = self.options.get("scan_type")
        timing = self.options.get("timing")
        service_detection = self.options.get("service_detection")
        
        # Build scan options
        scan_options = {
            "ports": ports,
            "service_detection": service_detection,
            "timing": timing,
        }
        
        # Add scan type flags
        if scan_type == "tcp":
            scan_args = ["-sT"]
        elif scan_type == "syn":
            scan_args = ["-sS"]
        elif scan_type == "udp":
            scan_args = ["-sU"]
        else:
            scan_args = []
        
        # Run the scan
        results = self.nmap.scan(target, *scan_args, **scan_options)
        
        # Format output based on selected format
        output_format = self.options.get("output_format")
        if output_format == "minimal":
            return self._format_minimal_output(results)
        else:
            return results
    
    def _format_minimal_output(self, results: dict) -> dict:
        """Format the output in a minimal format.
        
        Args:
            results: Scan results
            
        Returns:
            Formatted results
        """
        minimal = {
            "target": self.options.get("target"),
            "hosts": []
        }
        
        # Extract host and open port information
        for host in results.get("hosts", []):
            host_info = {
                "ip": host.get("ip_address"),
                "hostname": host.get("hostname"),
                "open_ports": []
            }
            
            for port in host.get("open_ports", []):
                if port.get("state") == "open":
                    host_info["open_ports"].append({
                        "port": port.get("port"),
                        "service": port.get("service"),
                        "protocol": port.get("protocol")
                    })
            
            minimal["hosts"].append(host_info)
        
        return minimal
