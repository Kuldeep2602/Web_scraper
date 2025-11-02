"""
State management for fault-tolerant scraping with checkpoint/resume functionality.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Set, Optional
from datetime import datetime
import threading


class StateManager:
    """
    Manages scraping state to enable resumption after interruption.
    Implements checkpoint functionality for fault tolerance.
    """
    
    def __init__(self, state_file: Path):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to state file for persistence
        """
        self.state_file = state_file
        self.state: Dict[str, Any] = self._load_state()
        self._lock = threading.Lock()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file or create new state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._create_new_state()
        return self._create_new_state()
    
    def _create_new_state(self) -> Dict[str, Any]:
        """Create a new state structure."""
        return {
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "projects": {},
            "completed_projects": [],
            "total_issues_scraped": 0,
            "last_checkpoint": None
        }
    
    def save_state(self):
        """Persist current state to disk."""
        with self._lock:
            self.state["last_updated"] = datetime.utcnow().isoformat()
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
            temp_file.replace(self.state_file)
    
    def init_project(self, project_key: str):
        """Initialize state for a new project."""
        with self._lock:
            if project_key not in self.state["projects"]:
                self.state["projects"][project_key] = {
                    "started_at": datetime.utcnow().isoformat(),
                    "status": "in_progress",
                    "scraped_issues": [],
                    "failed_issues": [],
                    "last_start_at": 0,
                    "total_issues": 0,
                    "issues_scraped": 0
                }
        self.save_state()
    
    def mark_issue_scraped(self, project_key: str, issue_key: str):
        """Mark an issue as successfully scraped."""
        with self._lock:
            if project_key in self.state["projects"]:
                if issue_key not in self.state["projects"][project_key]["scraped_issues"]:
                    self.state["projects"][project_key]["scraped_issues"].append(issue_key)
                    self.state["projects"][project_key]["issues_scraped"] += 1
                    self.state["total_issues_scraped"] += 1
    
    def mark_issue_failed(self, project_key: str, issue_key: str, error: str):
        """Mark an issue as failed."""
        with self._lock:
            if project_key in self.state["projects"]:
                self.state["projects"][project_key]["failed_issues"].append({
                    "issue_key": issue_key,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    def update_pagination(self, project_key: str, start_at: int, total: int):
        """Update pagination state for a project."""
        with self._lock:
            if project_key in self.state["projects"]:
                self.state["projects"][project_key]["last_start_at"] = start_at
                self.state["projects"][project_key]["total_issues"] = total
    
    def complete_project(self, project_key: str):
        """Mark a project as completed."""
        with self._lock:
            if project_key in self.state["projects"]:
                self.state["projects"][project_key]["status"] = "completed"
                self.state["projects"][project_key]["completed_at"] = datetime.utcnow().isoformat()
                if project_key not in self.state["completed_projects"]:
                    self.state["completed_projects"].append(project_key)
        self.save_state()
    
    def is_issue_scraped(self, project_key: str, issue_key: str) -> bool:
        """Check if an issue has already been scraped."""
        with self._lock:
            if project_key in self.state["projects"]:
                return issue_key in self.state["projects"][project_key]["scraped_issues"]
            return False
    
    def get_scraped_issues(self, project_key: str) -> Set[str]:
        """Get set of already scraped issue keys for a project."""
        with self._lock:
            if project_key in self.state["projects"]:
                return set(self.state["projects"][project_key]["scraped_issues"])
            return set()
    
    def get_last_pagination(self, project_key: str) -> int:
        """Get the last pagination position for resumption."""
        with self._lock:
            if project_key in self.state["projects"]:
                return self.state["projects"][project_key]["last_start_at"]
            return 0
    
    def is_project_completed(self, project_key: str) -> bool:
        """Check if a project is already completed."""
        with self._lock:
            return project_key in self.state["completed_projects"]
    
    def get_progress(self, project_key: str) -> Dict[str, Any]:
        """Get progress information for a project."""
        with self._lock:
            if project_key in self.state["projects"]:
                proj = self.state["projects"][project_key]
                return {
                    "total": proj["total_issues"],
                    "scraped": proj["issues_scraped"],
                    "failed": len(proj["failed_issues"]),
                    "percentage": (proj["issues_scraped"] / proj["total_issues"] * 100) 
                                  if proj["total_issues"] > 0 else 0
                }
            return {"total": 0, "scraped": 0, "failed": 0, "percentage": 0}
    
    def checkpoint(self):
        """Create a checkpoint of the current state."""
        with self._lock:
            self.state["last_checkpoint"] = datetime.utcnow().isoformat()
        self.save_state()
    
    def reset_project(self, project_key: str):
        """Reset state for a specific project."""
        with self._lock:
            if project_key in self.state["projects"]:
                del self.state["projects"][project_key]
            if project_key in self.state["completed_projects"]:
                self.state["completed_projects"].remove(project_key)
        self.save_state()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall summary of scraping progress."""
        with self._lock:
            return {
                "total_issues_scraped": self.state["total_issues_scraped"],
                "projects_completed": len(self.state["completed_projects"]),
                "projects_in_progress": len([p for p in self.state["projects"].values() 
                                            if p["status"] == "in_progress"]),
                "created_at": self.state["created_at"],
                "last_updated": self.state["last_updated"]
            }
