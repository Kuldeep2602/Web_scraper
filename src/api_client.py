"""
Robust API client for Jira with retry logic, rate limiting, and error handling.
"""
import asyncio
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from .config import Config


class RateLimiter:
    """Token bucket rate limiter for API requests."""
    
    def __init__(self, rate_limit: int):
        """
        Initialize rate limiter.
        
        Args:
            rate_limit: Maximum requests per second
        """
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self.lock:
            while self.tokens <= 0:
                self._add_tokens()
                if self.tokens <= 0:
                    await asyncio.sleep(0.1)
            
            self.tokens -= 1
    
    def _add_tokens(self):
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.updated_at
        new_tokens = elapsed * self.rate_limit
        self.tokens = min(self.rate_limit, self.tokens + new_tokens)
        self.updated_at = now


class JiraAPIClient:
    """
    Robust API client for Jira REST API with:
    - Exponential backoff retry logic
    - Rate limiting
    - Connection pooling
    - Error handling for network issues
    """
    
    def __init__(self, config: Config, logger: logging.Logger):
        """
        Initialize Jira API client.
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.rate_limiter = RateLimiter(config.RATE_LIMIT)
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = config.JIRA_BASE_URL
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def create_session(self):
        """Create aiohttp session with connection pooling."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.config.MAX_CONCURRENT_REQUESTS,
                limit_per_host=self.config.MAX_CONCURRENT_REQUESTS,
                ttl_dns_cache=300
            )
            timeout = aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Accept": "application/json"}
            )
    
    async def close_session(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            await asyncio.sleep(0.25)  # Allow time for connections to close
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type((
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ConnectionError
        )),
        before_sleep=before_sleep_log(logging.getLogger("jira_scraper"), logging.WARNING)
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            **kwargs: Additional request arguments
            
        Returns:
            JSON response as dictionary
            
        Raises:
            Various HTTP and network exceptions
        """
        await self.rate_limiter.acquire()
        
        if self.session is None:
            await self.create_session()
        
        try:
            async with self.session.request(method, url, params=params, **kwargs) as response:
                # Handle rate limiting (429)
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    self.logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited, retrying...")
                
                # Handle server errors (5xx)
                if 500 <= response.status < 600:
                    self.logger.error(f"Server error {response.status}. Retrying...")
                    raise aiohttp.ClientError(f"Server error: {response.status}")
                
                # Handle client errors (4xx except 429)
                if 400 <= response.status < 500:
                    error_text = await response.text()
                    self.logger.error(f"Client error {response.status}: {error_text}")
                    # Don't retry client errors (except 429 handled above)
                    return {}
                
                response.raise_for_status()
                
                # Handle empty responses
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                else:
                    self.logger.warning(f"Non-JSON response received: {content_type}")
                    return {}
                    
        except asyncio.TimeoutError:
            self.logger.error("Request timeout. Retrying...")
            raise
        except aiohttp.ClientError as e:
            self.logger.error(f"Request failed: {str(e)}. Retrying...")
            raise
    
    async def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 100,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for issues using JQL (Jira Query Language).
        
        Args:
            jql: JQL query string
            start_at: Pagination offset
            max_results: Maximum results per page
            fields: List of fields to retrieve
            
        Returns:
            Search results as dictionary
        """
        url = f"{self.base_url}/rest/api/2/search"
        
        if fields is None:
            fields = ["*all"]
        
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(fields)
        }
        
        self.logger.debug(f"Searching issues: {jql} (start={start_at}, max={max_results})")
        return await self._make_request("GET", url, params=params)
    
    async def get_issue(self, issue_key: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific issue.
        
        Args:
            issue_key: Issue key (e.g., "KAFKA-1234")
            expand: Optional comma-separated list of entities to expand
            
        Returns:
            Issue details as dictionary
        """
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        params = {}
        
        if expand:
            params["expand"] = expand
        
        self.logger.debug(f"Fetching issue: {issue_key}")
        return await self._make_request("GET", url, params=params)
    
    async def get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Get all comments for an issue.
        
        Args:
            issue_key: Issue key
            
        Returns:
            List of comments
        """
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
        
        self.logger.debug(f"Fetching comments for: {issue_key}")
        result = await self._make_request("GET", url)
        
        return result.get("comments", []) if result else []
    
    async def get_project_info(self, project_key: str) -> Dict[str, Any]:
        """
        Get project information.
        
        Args:
            project_key: Project key (e.g., "KAFKA")
            
        Returns:
            Project information
        """
        url = f"{self.base_url}/rest/api/2/project/{project_key}"
        
        self.logger.debug(f"Fetching project info: {project_key}")
        return await self._make_request("GET", url)
