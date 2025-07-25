"""
Project checking and filtering logic.

Handles project matching against user skills and other filtering logic.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ProjectChecker:
    """Handles project filtering and matching logic."""
    
    @staticmethod
    def project_matches_user_skills(project: Dict[str, Any], user_skills: List[int]) -> bool:
        """Check if project skills match user skills."""
        if not user_skills:
            return True  # If we can't get user skills, don't filter
        
        project_skills = project.get("attributes", {}).get("skills", [])
        project_skill_ids = [skill.get("id") for skill in project_skills if skill.get("id")]
        
        # Check if any project skill matches user skills
        matches = any(skill_id in user_skills for skill_id in project_skill_ids)
        
        if not matches:
            logger.debug(f"Project {project.get('id')} skills {project_skill_ids} don't match user skills {user_skills}")
        
        return matches
    
    @staticmethod
    def should_process_project(project: Dict[str, Any], user_filters: Dict[str, str], 
                             user_skills: List[int], sent_projects: set) -> bool:
        """
        Check if project should be processed and sent to user.
        
        Args:
            project: Project data from API
            user_filters: User's active filters
            user_skills: User's skill IDs
            sent_projects: Set of already sent project IDs
            
        Returns:
            True if project should be sent, False otherwise
        """
        project_id = project.get("id")
        
        # Skip if project has already been sent
        if project_id in sent_projects:
            logger.debug(f"Project {project_id} already sent, skipping")
            return False
        
        # Тимчасово відключена додаткова фільтрація за навичками користувача
        # оскільки фільтр only_my_skills працює тільки з персональним ключем
        # if user_filters.get("only_my_skills") == "1":
        #     if not ProjectChecker.project_matches_user_skills(project, user_skills):
        #         logger.info(f"Project {project_id} doesn't match user skills, skipping")
        #         return False
        
        return True
    
    @staticmethod
    def calculate_smart_interval(min_user_interval: int, active_users_count: int, 
                               rate_limit_remaining: int = None) -> int:
        """
        Calculate smart interval based on rate limits and user settings.
        
        Args:
            min_user_interval: Minimum interval from user settings
            active_users_count: Number of active users
            rate_limit_remaining: Remaining API requests
            
        Returns:
            Calculated smart interval in seconds
        """
        smart_interval = min_user_interval
        
        # Adjust interval based on rate limit status
        if rate_limit_remaining is not None:
            if rate_limit_remaining < 20:
                # If low on requests, increase interval
                smart_interval = max(min_user_interval, 120)  # At least 2 minutes
                logger.info(f"Low rate limit, increasing interval to {smart_interval}s")
            elif rate_limit_remaining < 10:
                # If very low, increase even more
                smart_interval = max(min_user_interval, 300)  # At least 5 minutes
                logger.warning(f"Very low rate limit, increasing interval to {smart_interval}s")
        
        # Additional delay for multiple active users to spread requests
        if active_users_count > 1:
            user_delay = active_users_count * 2  # 2 seconds per additional user
            smart_interval = max(smart_interval, user_delay)
            logger.info(f"Multiple users active, adjusted interval to {smart_interval}s")
        
        return smart_interval


# Global project checker instance
project_checker = ProjectChecker()