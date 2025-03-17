"""Data models for PenKit."""

from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    # For Python < 3.11
    from datetime import timezone
    UTC = timezone.utc
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Severity levels for vulnerabilities."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


class Status(str, Enum):
    """Status values for various entities."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    VERIFIED = "verified"
    FALSE_POSITIVE = "false_positive"


class HostStatus(str, Enum):
    """Status values for hosts."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class Port(BaseModel):
    """Model for a network port."""

    port: int
    protocol: str
    service: Optional[str] = None
    version: Optional[str] = None
    state: str = "open"
    banner: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        return data


class Host(BaseModel):
    """Model for a host."""

    id: Optional[str] = None
    ip_address: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    status: HostStatus = HostStatus.UNKNOWN
    mac_address: Optional[str] = None
    open_ports: List[Port] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        
        # Convert datetime objects
        data["first_seen"] = data["first_seen"].isoformat()
        data["last_seen"] = data["last_seen"].isoformat()
        
        # Convert nested objects
        data["open_ports"] = [p.to_dict() for p in self.open_ports]
        
        return data


class Vulnerability(BaseModel):
    """Model for a vulnerability."""

    id: Optional[str] = None
    title: str
    description: str
    severity: Severity = Severity.UNKNOWN
    status: Status = Status.OPEN
    cve_ids: List[str] = Field(default_factory=list)
    cvss_score: Optional[float] = None
    affected_hosts: List[str] = Field(default_factory=list)
    proof_of_concept: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("cvss_score")
    @classmethod
    def validate_cvss_score(cls, v: Optional[float]) -> Optional[float]:
        """Validate CVSS score.

        Args:
            v: CVSS score

        Returns:
            Validated CVSS score

        Raises:
            ValueError: If score is out of range
        """
        if v is not None and (v < 0 or v > 10):
            raise ValueError("CVSS score must be between 0 and 10")
        return v
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        
        # Convert datetime objects
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()
        
        return data


class ScanResult(BaseModel):
    """Model for a scan result."""

    id: Optional[str] = None
    tool: str
    command: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: str = "running"
    result_summary: Optional[Dict[str, Any]] = None
    hosts_discovered: List[Host] = Field(default_factory=list)
    vulnerabilities_found: List[Vulnerability] = Field(default_factory=list)
    raw_output: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def duration(self) -> Optional[float]:
        """Calculate scan duration in seconds.

        Returns:
            Duration in seconds if end_time is set, None otherwise
        """
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def is_complete(self) -> bool:
        """Check if the scan is complete.

        Returns:
            True if the scan is complete, False otherwise
        """
        return self.status != "running"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        
        # Convert datetime objects
        data["start_time"] = data["start_time"].isoformat()
        if data["end_time"]:
            data["end_time"] = data["end_time"].isoformat()
            
        # Convert nested objects
        data["hosts_discovered"] = [h.to_dict() for h in self.hosts_discovered]
        data["vulnerabilities_found"] = [v.to_dict() for v in self.vulnerabilities_found]
        
        return data


class Credential(BaseModel):
    """Model for a credential."""

    id: Optional[str] = None
    username: str
    password: Optional[str] = None
    hash: Optional[str] = None
    host: Optional[str] = None
    service: Optional[str] = None
    port: Optional[int] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        
        # Convert datetime objects
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()
        
        return data


class ToolResult(BaseModel):
    """Model for storing the result of a tool execution."""

    tool_name: str
    command: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    parsed_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.

        Returns:
            Dictionary representation
        """
        result = {
            "tool_name": self.tool_name,
            "command": self.command,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:200] + "..."
            if self.stdout and len(self.stdout) > 200
            else self.stdout,
            "stderr": self.stderr,
            "parsed_result": self.parsed_result,
        }
        return result


class NetworkRange(BaseModel):
    """Model for a network range."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    cidr: Optional[str] = None
    ip_range: Optional[str] = None
    hosts: List[Host] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        
        # Convert datetime objects
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()
        
        # Convert nested objects
        data["hosts"] = [h.to_dict() for h in self.hosts]
        
        return data


class Project(BaseModel):
    """Model for a project."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    status: str = "active"
    targets: List[Union[Host, NetworkRange]] = Field(default_factory=list)
    findings: List[Vulnerability] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable values.
        
        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        
        # Convert datetime objects
        data["start_date"] = data["start_date"].isoformat()
        if data["end_date"]:
            data["end_date"] = data["end_date"].isoformat()
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()
        
        # Convert nested objects
        data["targets"] = [t.to_dict() for t in self.targets]
        data["findings"] = [f.to_dict() for f in self.findings]
        
        return data