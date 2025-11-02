"""
Main entry point for the Jira scraper pipeline.
"""
import asyncio
import sys
from pathlib import Path

from .config import Config
from .logger import setup_logger
from .api_client import JiraAPIClient
from .state_manager import StateManager
from .scraper import JiraScraper
from .transformer import DataTransformer


async def main():
    """Main execution function."""
    
    # Setup
    Config.ensure_directories()
    logger = setup_logger(
        level=Config.LOG_LEVEL,
        log_file=Config.OUTPUT_DIR / "scraper.log"
    )
    
    logger.info("=" * 60)
    logger.info("JIRA DATA SCRAPER STARTED")
    logger.info("=" * 60)
    logger.info(f"Projects to scrape: {', '.join(Config.JIRA_PROJECTS)}")
    logger.info(f"Rate limit: {Config.RATE_LIMIT} req/s")
    logger.info(f"Max concurrent requests: {Config.MAX_CONCURRENT_REQUESTS}")
    logger.info(f"Output directory: {Config.OUTPUT_DIR}")
    logger.info("=" * 60)
    
    # Initialize components
    state_file = Config.get_state_path("scraper_state.json")
    state_manager = StateManager(state_file)
    
    transformer = DataTransformer(logger)
    
    try:
        # Create API client with context manager
        async with JiraAPIClient(Config, logger) as api_client:
            # Create scraper
            scraper = JiraScraper(api_client, state_manager, Config, logger)
            
            # Scrape all projects
            all_results = await scraper.scrape_all_projects()
            
            # Transform and save data
            logger.info("=" * 60)
            logger.info("STARTING DATA TRANSFORMATION")
            logger.info("=" * 60)
            
            all_examples = []
            
            for project_key, issues in all_results.items():
                if not issues:
                    logger.warning(f"No issues to transform for {project_key}")
                    continue
                
                logger.info(f"Transforming {len(issues)} issues from {project_key}...")
                
                # Transform issues
                examples = transformer.transform_batch(issues)
                all_examples.extend(examples)
                
                # Save project-specific JSONL
                project_output = Config.get_output_path(f"{project_key}_training_data.jsonl")
                transformer.save_to_jsonl(examples, str(project_output))
            
            # Save combined dataset
            if all_examples:
                combined_output = Config.get_output_path("combined_training_data.jsonl")
                transformer.save_to_jsonl(all_examples, str(combined_output))
                
                # Generate and save statistics
                stats = transformer.create_dataset_stats(all_examples)
                stats_output = Config.get_output_path("dataset_stats.json")
                
                import json
                with open(stats_output, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2, default=str)
                
                logger.info("=" * 60)
                logger.info("DATASET STATISTICS")
                logger.info("=" * 60)
                logger.info(f"Total training examples: {stats['total_examples']}")
                logger.info(f"Task distribution: {dict(stats['tasks'])}")
                logger.info(f"Project distribution: {dict(stats['projects'])}")
                logger.info("=" * 60)
            
            logger.info("=" * 60)
            logger.info("SCRAPING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"Output files saved to: {Config.OUTPUT_DIR}")
            logger.info(f"State saved to: {Config.STATE_DIR}")
            
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user. State has been saved.")
        state_manager.checkpoint()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        state_manager.checkpoint()
        sys.exit(1)


def run():
    """Entry point for running the scraper."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScraping interrupted. You can resume later.")
        sys.exit(0)


if __name__ == "__main__":
    run()
