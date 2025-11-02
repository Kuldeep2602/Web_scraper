"""
Data scraper for Apache Jira with pagination and fault tolerance.
"""
import asyncio
from typing import Dict, Any, List, Optional
from tqdm.asyncio import tqdm
import logging

from .api_client import JiraAPIClient
from .state_manager import StateManager
from .config import Config


class JiraScraper:
    """
    Main scraper class that orchestrates data collection from Jira.
    Handles pagination, retries, and state management.
    """
    
    def __init__(
        self,
        api_client: JiraAPIClient,
        state_manager: StateManager,
        config: Config,
        logger: logging.Logger
    ):
        """
        Initialize scraper.
        
        Args:
            api_client: Jira API client
            state_manager: State manager for checkpointing
            config: Configuration object
            logger: Logger instance
        """
        self.api_client = api_client
        self.state_manager = state_manager
        self.config = config
        self.logger = logger
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
    
    async def scrape_project(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Scrape all issues from a project.
        
        Args:
            project_key: Jira project key (e.g., "KAFKA")
            
        Returns:
            List of scraped issues with full details
        """
        self.logger.info(f"Starting scrape for project: {project_key}")
        
        # Check if project is already completed
        if self.state_manager.is_project_completed(project_key):
            self.logger.info(f"Project {project_key} already completed. Skipping...")
            return []
        
        # Initialize project state
        self.state_manager.init_project(project_key)
        
        # Get project info
        try:
            project_info = await self.api_client.get_project_info(project_key)
            self.logger.info(f"Project: {project_info.get('name', project_key)}")
        except Exception as e:
            self.logger.error(f"Failed to get project info for {project_key}: {str(e)}")
            project_info = {}
        
        all_issues = []
        start_at = self.state_manager.get_last_pagination(project_key)
        
        # Build JQL query
        jql = f"project = {project_key} ORDER BY created DESC"
        
        # Initial search to get total count
        try:
            initial_result = await self.api_client.search_issues(
                jql=jql,
                start_at=start_at,
                max_results=self.config.ISSUES_PER_PAGE
            )
            
            total_issues = initial_result.get("total", 0)
            self.logger.info(f"Total issues in {project_key}: {total_issues}")
            
            if total_issues == 0:
                self.logger.warning(f"No issues found for project {project_key}")
                self.state_manager.complete_project(project_key)
                return []
            
        except Exception as e:
            self.logger.error(f"Failed initial search for {project_key}: {str(e)}")
            return []
        
        # Paginate through all issues
        with tqdm(total=total_issues, initial=start_at, desc=f"Scraping {project_key}") as pbar:
            while start_at < total_issues:
                try:
                    # Search for issues
                    search_result = await self.api_client.search_issues(
                        jql=jql,
                        start_at=start_at,
                        max_results=self.config.ISSUES_PER_PAGE
                    )
                    
                    issues = search_result.get("issues", [])
                    
                    if not issues:
                        self.logger.warning(f"No issues returned at offset {start_at}")
                        break
                    
                    # Update pagination state
                    self.state_manager.update_pagination(
                        project_key,
                        start_at,
                        search_result.get("total", total_issues)
                    )
                    
                    # Process issues concurrently
                    tasks = [
                        self._process_issue(issue, project_key)
                        for issue in issues
                    ]
                    
                    processed_issues = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Filter out failed issues and exceptions
                    for issue in processed_issues:
                        if isinstance(issue, Exception):
                            self.logger.error(f"Issue processing failed: {str(issue)}")
                        elif issue:
                            all_issues.append(issue)
                    
                    # Update progress
                    pbar.update(len(issues))
                    start_at += len(issues)
                    
                    # Checkpoint periodically
                    if len(all_issues) % (self.config.ISSUES_PER_PAGE * 5) == 0:
                        self.state_manager.checkpoint()
                        self.logger.info(f"Checkpoint saved at {len(all_issues)} issues")
                    
                except Exception as e:
                    self.logger.error(f"Error during pagination at {start_at}: {str(e)}")
                    # Save state and continue
                    self.state_manager.save_state()
                    break
        
        # Mark project as completed
        self.state_manager.complete_project(project_key)
        self.logger.info(f"Completed scraping {project_key}: {len(all_issues)} issues")
        
        return all_issues
    
    async def _process_issue(self, issue_data: Dict[str, Any], project_key: str) -> Optional[Dict[str, Any]]:
        """
        Process a single issue: fetch full details and comments.
        
        Args:
            issue_data: Basic issue data from search
            project_key: Project key
            
        Returns:
            Enriched issue data or None if failed
        """
        async with self.semaphore:
            issue_key = issue_data.get("key")
            
            if not issue_key:
                self.logger.warning("Issue without key encountered")
                return None
            
            # Skip if already scraped
            if self.state_manager.is_issue_scraped(project_key, issue_key):
                return None
            
            try:
                # Get full issue details with expansions
                full_issue = await self.api_client.get_issue(
                    issue_key,
                    expand="changelog,renderedFields"
                )
                
                # Get comments
                comments = await self.api_client.get_comments(issue_key)
                
                # Combine data
                enriched_issue = {
                    **full_issue,
                    "comments_data": comments
                }
                
                # Mark as scraped
                self.state_manager.mark_issue_scraped(project_key, issue_key)
                
                return enriched_issue
                
            except Exception as e:
                error_msg = f"Failed to process {issue_key}: {str(e)}"
                self.logger.error(error_msg)
                self.state_manager.mark_issue_failed(project_key, issue_key, str(e))
                return None
    
    async def scrape_all_projects(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape all configured projects.
        
        Returns:
            Dictionary mapping project keys to their issues
        """
        all_results = {}
        
        for project_key in self.config.JIRA_PROJECTS:
            try:
                issues = await self.scrape_project(project_key.strip())
                all_results[project_key] = issues
                
                # Small delay between projects
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Failed to scrape project {project_key}: {str(e)}")
                all_results[project_key] = []
        
        # Final checkpoint
        self.state_manager.checkpoint()
        
        # Print summary
        summary = self.state_manager.get_summary()
        self.logger.info("=" * 60)
        self.logger.info("SCRAPING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total issues scraped: {summary['total_issues_scraped']}")
        self.logger.info(f"Projects completed: {summary['projects_completed']}")
        self.logger.info(f"Projects in progress: {summary['projects_in_progress']}")
        self.logger.info("=" * 60)
        
        return all_results
