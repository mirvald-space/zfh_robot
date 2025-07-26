"""
Project checker utility.

Handles project filtering and processing logic.
"""

import logging
from typing import Dict, Any, List, Set, Dict

import config

logger = logging.getLogger(__name__)


class ProjectChecker:
    """Handles project filtering and processing logic."""
    
    def should_process_project(self, project: Dict[str, Any], 
                             filters: Dict[str, str], 
                             user_skills: List[int],
                             user_id: int,
                             user_sent_projects: Dict[int, Set[int]]) -> bool:
        """
        Check if project should be processed and sent to user.
        
        Args:
            project: Project data from API
            filters: User filter settings
            user_skills: User skills IDs list
            user_id: Telegram user ID
            user_sent_projects: Dictionary of sent projects by user ID
            
        Returns:
            True if project should be processed, False otherwise
        """
        project_id = project.get("id")
        
        # Check if project ID is valid
        if not project_id:
            logger.warning("Project has no ID, skipping")
            return False
        
        # Check if project was already sent to this user
        if user_id in user_sent_projects and project_id in user_sent_projects.get(user_id, set()):
            logger.info(f"Project {project_id} already sent to user {user_id}, skipping")
            return False
        
        # Get project attributes
        attributes = project.get("attributes", {})
        
        # Get project status
        status = attributes.get("status", {})
        status_id = status.get("id")
        status_name = status.get("name", "")
        
        # Only accept projects with status ID 11 (Open for proposals)
        if status_id != 11:
            logger.info(f"Project {project_id} has status ID {status_id} ({status_name}), skipping (only status ID 11 is allowed)")
            return False
        
        # Check employer ID filter
        if filters.get("employer_id"):
            employer_id = attributes.get("employer", {}).get("id")
            filter_employer_id = filters["employer_id"]
            
            if str(employer_id) != str(filter_employer_id):
                logger.info(f"Project {project_id} employer {employer_id} doesn't match filter {filter_employer_id}, skipping")
                return False
        
        # Check if project is for Plus profiles only
        if filters.get("only_for_plus") == "1":
            is_only_for_plus = attributes.get("only_for_plus", False)
            if not is_only_for_plus:
                logger.info(f"Project {project_id} is not for Plus profiles only, skipping")
                return False
        
        # Check skills filter
        if filters.get("skill_id"):
            project_skills = [skill.get("id") for skill in attributes.get("skills", [])]
            filter_skills = list(map(int, filters["skill_id"].split(",")))
            
            # Check if project has at least one skill from the filter
            has_skill = any(skill in project_skills for skill in filter_skills)
            if not has_skill:
                logger.info(f"Project {project_id} skills {project_skills} don't match filter skills {filter_skills}, skipping")
                return False
        
        # Проверка фильтра only_my_skills отключена, т.к. требует персональный API ключ
        # if filters.get("only_my_skills") == "1":
        #     project_skills = [skill.get("id") for skill in attributes.get("skills", [])]
        #     if not any(skill in project_skills for skill in user_skills):
        #         logger.info(f"Project {project_id} skills {project_skills} don't match user skills {user_skills}, skipping")
        #         return False
        
        # Project passes all checks
        logger.info(f"Project {project_id} passed all filters, will be sent to user {user_id}")
        return True
    
    def calculate_smart_interval(self, min_user_interval: int, 
                               active_users_count: int, 
                               api_requests_remaining: int = None) -> int:
        """
        Calculate smart interval for project checks based on various factors.
        
        Args:
            min_user_interval: Minimum interval among all active users
            active_users_count: Number of active users
            api_requests_remaining: Remaining API requests count
            
        Returns:
            Calculated interval in seconds
        """
        # Start with user-defined interval
        interval = min_user_interval
        
        # Adjust based on number of active users
        if active_users_count > 10:
            # For many users, increase interval to prevent API rate limits
            interval = max(interval, 60)  # At least 60 seconds
        
        # Adjust based on API rate limit
        if api_requests_remaining is not None:
            if api_requests_remaining < 5:
                # Very low remaining requests, slow down significantly
                interval = max(interval, 300)  # At least 5 minutes
            elif api_requests_remaining < 10:
                # Low remaining requests, slow down
                interval = max(interval, 120)  # At least 2 minutes
        
        return interval


project_checker = ProjectChecker()