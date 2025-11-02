"""
Jira Data Scraper and Transformer
A robust pipeline for scraping Apache Jira and preparing LLM training data.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .config import Config
from .logger import setup_logger
from .api_client import JiraAPIClient
from .state_manager import StateManager
from .scraper import JiraScraper
from .transformer import DataTransformer

__all__ = [
    "Config",
    "setup_logger",
    "JiraAPIClient",
    "StateManager",
    "JiraScraper",
    "DataTransformer",
]
