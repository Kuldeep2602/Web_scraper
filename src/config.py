"""
Configuration management for Jira scraper.
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the Jira scraper."""
    
    # Jira API settings
    JIRA_BASE_URL: str = os.getenv("JIRA_BASE_URL", "https://issues.apache.org/jira")
    JIRA_PROJECTS: List[str] = os.getenv("JIRA_PROJECTS", "KAFKA,SPARK,AIRFLOW").split(",")
    
    # Rate limiting
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "10"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    
    # Pagination
    ISSUES_PER_PAGE: int = int(os.getenv("ISSUES_PER_PAGE", "100"))
    
    # Retry configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
    RETRY_BACKOFF_FACTOR: int = int(os.getenv("RETRY_BACKOFF_FACTOR", "2"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Output configuration
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./output"))
    STATE_DIR: Path = Path(os.getenv("STATE_DIR", "./state"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """Construct full API URL."""
        return f"{cls.JIRA_BASE_URL}/rest/api/2/{endpoint.lstrip('/')}"
    
    @classmethod
    def get_output_path(cls, filename: str) -> Path:
        """Get full path for output file."""
        return cls.OUTPUT_DIR / filename
    
    @classmethod
    def get_state_path(cls, filename: str) -> Path:
        """Get full path for state file."""
        return cls.STATE_DIR / filename
