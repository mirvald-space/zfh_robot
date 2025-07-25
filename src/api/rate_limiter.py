"""
Rate limiting manager for Freelancehunt API.

Manages API rate limits to prevent HTTP 429 errors.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import config

logger = logging.getLogger(__name__)


class RateLimitManager:
    """Manages API rate limiting to prevent HTTP 429 errors."""
    
    def __init__(self):
        self.limit: Optional[int] = None
        self.remaining: Optional[int] = None
        self.last_request_time: Optional[datetime] = None
        self.min_interval_between_requests = config.MIN_API_REQUEST_INTERVAL
        
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit info from API response headers."""
        try:
            if 'X-Ratelimit-Limit' in headers:
                self.limit = int(headers['X-Ratelimit-Limit'])
            if 'X-Ratelimit-Remaining' in headers:
                self.remaining = int(headers['X-Ratelimit-Remaining'])
                
            logger.info(f"Rate limit updated: {self.remaining}/{self.limit} remaining")
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    async def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        
        # Always wait minimum interval between requests
        if self.last_request_time:
            time_since_last = (now - self.last_request_time).total_seconds()
            if time_since_last < self.min_interval_between_requests:
                wait_time = self.min_interval_between_requests - time_since_last
                logger.info(f"Waiting {wait_time:.1f}s to respect minimum interval")
                await asyncio.sleep(wait_time)
        
        # If we're running low on requests, wait longer
        if self.remaining is not None and self.remaining < config.RATE_LIMIT_WARNING_THRESHOLD:
            wait_time = 5.0  # Wait 5 seconds if below warning threshold
            logger.warning(f"Low rate limit remaining ({self.remaining}), waiting {wait_time}s")
            await asyncio.sleep(wait_time)
        elif self.remaining is not None and self.remaining < config.RATE_LIMIT_CRITICAL_THRESHOLD:
            wait_time = 10.0  # Wait 10 seconds if below critical threshold
            logger.warning(f"Very low rate limit remaining ({self.remaining}), waiting {wait_time}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
    
    def should_skip_request(self) -> bool:
        """Check if we should skip the request due to rate limits."""
        if self.remaining is not None and self.remaining <= 1:
            logger.error("Rate limit exhausted, skipping request")
            return True
        return False
    
    def get_status(self) -> str:
        """Get current rate limit status as string."""
        if self.limit and self.remaining is not None:
            return f"{self.remaining}/{self.limit} requests remaining"
        return "Rate limit status unknown"


# Global rate limit manager instance
rate_limiter = RateLimitManager()