"""Session management for PenKit."""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


class Target(Base):
    """Database model for a target."""

    __tablename__ = "targets"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.String, nullable=True)
    ip_address = sa.Column(sa.String, nullable=True)
    hostname = sa.Column(sa.String, nullable=True)
    os = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.String, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Finding(Base):
    """Database model for a finding."""

    __tablename__ = "findings"

    id = sa.Column(sa.Integer, primary_key=True)
    target_id = sa.Column(sa.Integer, sa.ForeignKey("targets.id"), nullable=False)
    name = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.String, nullable=True)
    severity = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.String, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Session:
    """A session represents a pentest engagement or project."""

    def __init__(self, name: str, path: Optional[Path] = None) -> None:
        """Initialize a new session.

        Args:
            name: The session name
            path: Path to store session data (default: ~/.penkit/sessions/<name>)
        """
        self.name = name
        
        if path is None:
            self.path = Path.home() / ".penkit" / "sessions" / name
        else:
            self.path = path / "sessions" / name
        
        self.path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.path / "session.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Session metadata
        self.metadata: Dict[str, Any] = {
            "name": name,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }
        
        # Save session metadata
        self._save_metadata()
    
    def _save_metadata(self) -> None:
        """Save session metadata to disk."""
        metadata_path = self.path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update session metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.metadata["updated_at"] = datetime.datetime.utcnow().isoformat()
        self._save_metadata()
    
    def add_target(self, name: str, **kwargs: Any) -> Target:
        """Add a target to the session.

        Args:
            name: Target name
            **kwargs: Additional target data

        Returns:
            The created target
        """
        with self.Session() as db_session:
            target = Target(name=name, **kwargs)
            db_session.add(target)
            db_session.commit()
            db_session.refresh(target)
            return target
    
    def get_targets(self) -> List[Target]:
        """Get all targets in the session.

        Returns:
            List of targets
        """
        with self.Session() as db_session:
            return db_session.query(Target).all()
    
    def get_target(self, target_id: int) -> Optional[Target]:
        """Get a target by ID.

        Args:
            target_id: Target ID

        Returns:
            The target if found, None otherwise
        """
        with self.Session() as db_session:
            return db_session.query(Target).filter(Target.id == target_id).first()
    
    def add_finding(self, target_id: int, name: str, **kwargs: Any) -> Finding:
        """Add a finding to a target.

        Args:
            target_id: Target ID
            name: Finding name
            **kwargs: Additional finding data

        Returns:
            The created finding
        """
        with self.Session() as db_session:
            finding = Finding(target_id=target_id, name=name, **kwargs)
            db_session.add(finding)
            db_session.commit()
            db_session.refresh(finding)
            return finding
    
    def get_findings(self, target_id: Optional[int] = None) -> List[Finding]:
        """Get all findings in the session.

        Args:
            target_id: Filter by target ID (optional)

        Returns:
            List of findings
        """
        with self.Session() as db_session:
            query = db_session.query(Finding)
            if target_id is not None:
                query = query.filter(Finding.target_id == target_id)
            return query.all()
    
    def save_scan_result(self, tool_name: str, result: Any) -> None:
        """Save a scan result to disk.

        Args:
            tool_name: The tool that generated the result
            result: The scan result (will be serialized to JSON)
        """
        results_dir = self.path / "results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        result_path = results_dir / f"{tool_name}_{timestamp}.json"
        
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)
    
    def save_artifact(self, name: str, content: str, extension: str = "txt") -> None:
        """Save an artifact to disk.

        Args:
            name: Artifact name
            content: Artifact content
            extension: File extension (default: txt)
        """
        artifacts_dir = self.path / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        artifact_path = artifacts_dir / f"{name}.{extension}"
        
        with open(artifact_path, "w") as f:
            f.write(content)
    
    def get_artifact(self, name: str, extension: str = "txt") -> Optional[str]:
        """Get an artifact from disk.

        Args:
            name: Artifact name
            extension: File extension (default: txt)

        Returns:
            The artifact content if found, None otherwise
        """
        artifact_path = self.path / "artifacts" / f"{name}.{extension}"
        
        if artifact_path.exists():
            with open(artifact_path, "r") as f:
                return f.read()
        
        return None


class SessionManager:
    """Manager for PenKit sessions."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialize the session manager.

        Args:
            base_path: Base path for sessions (default: ~/.penkit)
        """
        if base_path is None:
            self.base_path = Path.home() / ".penkit"
        else:
            self.base_path = base_path
        
        self.sessions_dir = self.base_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session(self, name: str) -> Session:
        """Create a new session.

        Args:
            name: Session name

        Returns:
            The created session

        Raises:
            ValueError: If a session with the same name already exists
        """
        session_dir = self.sessions_dir / name
        if session_dir.exists():
            raise ValueError(f"Session '{name}' already exists")
        
        return Session(name, self.base_path)
    
    def get_session(self, name: str) -> Optional[Session]:
        """Get a session by name.

        Args:
            name: Session name

        Returns:
            The session if found, None otherwise
        """
        session_dir = self.sessions_dir / name
        if not session_dir.exists():
            return None
        
        return Session(name, self.base_path)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions.

        Returns:
            List of session metadata dictionaries
        """
        sessions = []
        
        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                metadata_path = session_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        try:
                            metadata = json.load(f)
                            sessions.append(metadata)
                        except json.JSONDecodeError:
                            # Skip invalid metadata files
                            pass
        
        return sessions
    
    def delete_session(self, name: str) -> bool:
        """Delete a session.

        Args:
            name: Session name

        Returns:
            True if successful, False otherwise
        """
        session_dir = self.sessions_dir / name
        if not session_dir.exists():
            return False
        
        # Recursive delete
        for item in session_dir.glob("**/*"):
            if item.is_file():
                item.unlink()
        
        for item in sorted(session_dir.glob("**/*"), key=lambda x: len(str(x)), reverse=True):
            if item.is_dir():
                item.rmdir()
        
        session_dir.rmdir()
        return True
