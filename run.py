#!/usr/bin/env python3
"""
Command-line interface for the Jira scraper.
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import run
from src.config import Config


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Apache Jira Data Scraper for LLM Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (from .env file)
  python run.py

  # Run with specific projects
  python run.py --projects KAFKA SPARK AIRFLOW

  # Run with custom rate limit
  python run.py --rate-limit 5

  # Resume from previous state
  python run.py --resume

  # Reset state for a specific project
  python run.py --reset-project KAFKA
        """
    )
    
    parser.add_argument(
        "--projects",
        nargs="+",
        help="Jira project keys to scrape (e.g., KAFKA SPARK AIRFLOW)"
    )
    
    parser.add_argument(
        "--rate-limit",
        type=int,
        help="Maximum requests per second"
    )
    
    parser.add_argument(
        "--max-concurrent",
        type=int,
        help="Maximum concurrent requests"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for data files"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last saved state"
    )
    
    parser.add_argument(
        "--reset-project",
        type=str,
        help="Reset state for a specific project"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Override config with CLI arguments
    if args.projects:
        Config.JIRA_PROJECTS = args.projects
    
    if args.rate_limit:
        Config.RATE_LIMIT = args.rate_limit
    
    if args.max_concurrent:
        Config.MAX_CONCURRENT_REQUESTS = args.max_concurrent
    
    if args.output_dir:
        Config.OUTPUT_DIR = args.output_dir
    
    if args.log_level:
        Config.LOG_LEVEL = args.log_level
    
    # Handle reset
    if args.reset_project:
        from src.state_manager import StateManager
        state_file = Config.get_state_path("scraper_state.json")
        state_manager = StateManager(state_file)
        state_manager.reset_project(args.reset_project)
        print(f"State reset for project: {args.reset_project}")
        return
    
    # Run scraper
    print("Starting Jira scraper...")
    print(f"Projects: {', '.join(Config.JIRA_PROJECTS)}")
    print(f"Rate limit: {Config.RATE_LIMIT} req/s")
    print()
    
    run()


if __name__ == "__main__":
    main()
