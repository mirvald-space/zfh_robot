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
    """
    Manages API rate limiting to prevent HTTP 429 errors.
    
    Freelancehunt API does not explicitly document their rate limits.
    This manager implements a conservative approach using default values
    and adaptive behavior based on response headers if available.
    
    Default rate limit is set to 30 requests per minute, which is a 
    common practice for many REST APIs.
    """
    
    def __init__(self):
        self.limit: Optional[int] = None
        self.remaining: Optional[int] = None
        self.last_request_time: Optional[datetime] = None
        self.min_interval_between_requests = config.MIN_API_REQUEST_INTERVAL
        
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit info from API response headers.
        
        Tries to find rate limit headers in different formats and casings:
        - X-Ratelimit-Limit / X-Ratelimit-Remaining
        - X-Rate-Limit-Limit / X-Rate-Limit-Remaining
        or other variations that might contain 'ratelimit' in the header name.
        """
        try:
            # Check for various header casings and formats
            limit_found = False
            remaining_found = False
            
            # Check all headers for rate limit information
            for header, value in headers.items():
                header_lower = header.lower()
                
                # Try to find limit header
                if 'x-ratelimit-limit' in header_lower:
                    try:
                        self.limit = int(value)
                        limit_found = True
                    except (ValueError, TypeError):
                        pass
                    
                # Try to find remaining header
                if 'x-ratelimit-remaining' in header_lower:
                    try:
                        self.remaining = int(value)
                        remaining_found = True
                    except (ValueError, TypeError):
                        pass
                    
                # Some APIs use different header formats
                if 'x-rate-limit-limit' in header_lower and not limit_found:
                    try:
                        self.limit = int(value)
                        limit_found = True
                    except (ValueError, TypeError):
                        pass
                    
                if 'x-rate-limit-remaining' in header_lower and not remaining_found:
                    try:
                        self.remaining = int(value)
                        remaining_found = True
                    except (ValueError, TypeError):
                        pass
            
            if limit_found or remaining_found:
                logger.info(f"Rate limit updated: {self.remaining}/{self.limit} remaining")
            else:
                logger.warning("No rate limit headers found in response")
                
        except Exception as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    async def wait_if_needed(self) -> None:
        """
        Wait if necessary to respect rate limits.
        
        Implements an adaptive waiting strategy:
        1. Always wait minimum interval between requests
        2. If remaining requests are below warning threshold, wait longer
        3. If remaining requests are below critical threshold, wait even longer
        """
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
        if self.limit is not None and self.remaining is not None:
            # Calculate percentage
            percentage = (self.remaining / self.limit) * 100 if self.limit > 0 else 0
            status_emoji = "✅" if percentage > 50 else "⚠️" if percentage > 20 else "🚫"
            return f"{status_emoji} {self.remaining}/{self.limit} запросов ({percentage:.0f}%)"
        elif self.limit is not None:
            return f"Лимит: {self.limit} запросов (осталось: неизвестно)"
        elif self.remaining is not None:
            return f"Осталось {self.remaining} запросов (лимит: неизвестно)"
        else:
            return "Используются стандартные лимиты API (30 запросов/мин)"


# Global rate limit manager instance
rate_limiter = RateLimitManager()