"""
Freelancehunt API client.

Handles all interactions with Freelancehunt API including projects and user profile.
"""

import json
import logging
from typing import Dict, List, Any

import aiohttp

import config
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class FreelancehuntAPI:
    """Client for Freelancehunt API."""
    
    BASE_URL = "https://api.freelancehunt.com/v2"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {config.FREELANCEHUNT_TOKEN}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(self, endpoint: str, params: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Make a request to Freelancehunt API with rate limiting.
        
        Note on rate limits:
        Freelancehunt API does not explicitly document rate limits in their API documentation.
        Based on common practices and experience with similar APIs, we're using a conservative 
        default of 30 requests per minute. The API may return actual rate limit information 
        in response headers, but if not, we'll use these defaults.
        """
        # Check rate limits before making request
        if rate_limiter.should_skip_request():
            logger.warning(f"Skipping request to {endpoint} due to rate limit")
            return {}
        
        # Wait if needed to respect rate limits
        await rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}{endpoint}"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url += f"?{query_string}"
        
        logger.info(f"Making API request to: {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    # Update rate limit info from response headers
                    headers_dict = dict(response.headers)
                    
                    # Check for rate limit headers only, without logging all headers
                    ratelimit_headers = {}
                    for header_name, header_value in headers_dict.items():
                        header_lower = header_name.lower()
                        if 'ratelimit' in header_lower:
                            ratelimit_headers[header_name] = header_value
                    
                    # Only log if we found relevant headers
                    if ratelimit_headers:
                        logger.debug(f"Rate limit headers found: {ratelimit_headers}")
                    
                    rate_limiter.update_from_headers(headers_dict)
                    
                    if response.status == 200:
                        # Get the response data
                        response_data = await response.json()
                        
                        # Check if rate limit info is in the response body
                        # Some APIs include rate limit in a "meta" field
                        if "meta" in response_data:
                            meta = response_data.get("meta", {})
                            if "ratelimit" in meta or "rate_limit" in meta:
                                rate_limit_info = meta.get("ratelimit", {}) or meta.get("rate_limit", {})
                                logger.debug(f"Rate limit info from body: {rate_limit_info}")
                                
                                # Update rate limiter from body data
                                if "limit" in rate_limit_info and "remaining" in rate_limit_info:
                                    try:
                                        limit_value = int(rate_limit_info["limit"])
                                        remaining_value = int(rate_limit_info["remaining"])
                                        rate_limiter.limit = limit_value
                                        rate_limiter.remaining = remaining_value
                                        logger.debug(f"Updated rate limits from body: {remaining_value}/{limit_value}")
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Failed to parse rate limit from body: {e}")
                        
                        # If we still don't have rate limit info, set default values
                        if rate_limiter.limit is None:
                            rate_limiter.limit = 30  # Default per minute based on common API practices
                            rate_limiter.remaining = 29  # Conservative default
                            logger.debug("Using default rate limit values (30 requests/minute)")
                        
                        return response_data
                    elif response.status == 429:
                        logger.error("Rate limit exceeded (HTTP 429)")
                        rate_limiter.remaining = 0
                        return {}
                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        return {}
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {e}")
                return {}
    
    async def get_projects(self, filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Get projects from Freelancehunt API with optional filters.
        
        API Documentation: https://apidocs.freelancehunt.com/#0eed992e-18f1-4dc4-892d-22b9d896935b
        Endpoint: GET /v2/projects
        """
        params = {}
        
        # Build filter parameters
        # ВАЖНО: При добавлении новых фильтров проверьте документацию API:
        # https://apidocs.freelancehunt.com/#0eed992e-18f1-4dc4-892d-22b9d896935b
        if filters:
            for key, value in filters.items():
                # Временно отключен фильтр only_my_skills так как работает только с персональным ключом
                # if key == "only_my_skills" and value == "1":
                #     params["filter[only_my_skills]"] = "1"
                if key == "skill_id" and value:
                    params["filter[skill_id]"] = value
                elif key == "employer_id" and value:
                    params["filter[employer_id]"] = value
                elif key == "only_for_plus" and value == "1":
                    params["filter[only_for_plus]"] = "1"
        
        logger.info(f"Fetching projects with filters: {filters}")
        logger.info(f"API request params: {params}")
        
        data = await self._make_request("/projects", params)
        projects = data.get("data", [])
        
        logger.info(f"Received {len(projects)} projects from API")
        
        return projects
    
    # Временно отключен метод get_user_profile так как требует персональный API ключ
    # async def get_user_profile(self) -> Dict[str, Any]:
    #     """
    #     Get user profile from Freelancehunt API.
    #     
    #     API Documentation: https://apidocs.freelancehunt.com/#0eed992e-18f1-4dc4-892d-22b9d896935b
    #     Endpoint: GET /v2/my/profile
    #     """
    #     logger.info("Fetching user profile")
    #     
    #     data = await self._make_request("/my/profile")
    #     return data.get("data", {})
    
    # Временно отключен метод get_user_skills так как требует персональный API ключ
    # async def get_user_skills(self) -> List[int]:
    #     """Get user's skills IDs from profile."""
    #     try:
    #         profile = await self.get_user_profile()
    #         attributes = profile.get("attributes", {})
    #         skills = attributes.get("skills", [])
    #         skill_ids = [skill.get("id") for skill in skills if skill.get("id")]
    #         
    #         logger.info(f"Retrieved {len(skill_ids)} user skills: {skill_ids}")
    #         return skill_ids
    #     except Exception as e:
    #         logger.error(f"Error fetching user skills: {e}")
    #         return []


# Global API client instance
api_client = FreelancehuntAPI()