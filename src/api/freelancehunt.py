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
        """Make a request to Freelancehunt API with rate limiting."""
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
                    rate_limiter.update_from_headers(dict(response.headers))
                    
                    if response.status == 200:
                        return await response.json()
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
        
        # Log the first project structure for debugging
        if projects and len(projects) > 0:
            logger.info(f"Sample project structure: {json.dumps(projects[0], indent=2, ensure_ascii=False)[:500]}...")
        
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