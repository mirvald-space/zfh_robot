"""
User state management.

Manages user states, filters, intervals and sent projects.
"""

import logging
from typing import Dict, Set

import config

logger = logging.getLogger(__name__)


class UserManager:
    """Manages user states and settings."""
    
    def __init__(self):
        self.active_users: Set[int] = set()
        self.user_filters: Dict[int, Dict[str, str]] = {}
        self.user_intervals: Dict[int, int] = {}
        self.sent_projects: Set[int] = set()
    
    def activate_user(self, user_id: int) -> None:
        """Activate notifications for user."""
        self.active_users.add(user_id)
        
        # Set default interval if not set
        if user_id not in self.user_intervals:
            self.user_intervals[user_id] = config.DEFAULT_CHECK_INTERVAL
        
        # Set empty filter if not set
        if user_id not in self.user_filters:
            self.user_filters[user_id] = {}
        
        logger.info(f"User {user_id} activated")
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate notifications for user. Returns True if user was active."""
        if user_id in self.active_users:
            self.active_users.remove(user_id)
            logger.info(f"User {user_id} deactivated")
            return True
        return False
    
    def is_user_active(self, user_id: int) -> bool:
        """Check if user is active."""
        return user_id in self.active_users
    
    def set_user_interval(self, user_id: int, interval: int) -> None:
        """Set check interval for user."""
        # Validate interval
        if interval < config.MIN_CHECK_INTERVAL:
            interval = config.MIN_CHECK_INTERVAL
        elif interval > config.MAX_CHECK_INTERVAL:
            interval = config.MAX_CHECK_INTERVAL
        
        self.user_intervals[user_id] = interval
        logger.info(f"User {user_id} interval set to {interval}s")
    
    def get_user_interval(self, user_id: int) -> int:
        """Get check interval for user."""
        return self.user_intervals.get(user_id, config.DEFAULT_CHECK_INTERVAL)
    
    def set_user_filters(self, user_id: int, filters: Dict[str, str]) -> None:
        """Set filters for user."""
        self.user_filters[user_id] = filters.copy()
        logger.info(f"User {user_id} filters updated: {filters}")
    
    def get_user_filters(self, user_id: int) -> Dict[str, str]:
        """Get filters for user."""
        return self.user_filters.get(user_id, {})
    
    def clear_user_filters(self, user_id: int) -> None:
        """Clear all filters for user."""
        self.user_filters[user_id] = {}
        logger.info(f"User {user_id} filters cleared")
    
    def add_sent_project(self, project_id: int) -> None:
        """Mark project as sent."""
        self.sent_projects.add(project_id)
    
    def is_project_sent(self, project_id: int) -> bool:
        """Check if project was already sent."""
        return project_id in self.sent_projects
    
    def cleanup_sent_projects(self, max_size: int = 1000, keep_size: int = 500) -> None:
        """Clean up sent projects if list gets too large."""
        if len(self.sent_projects) > max_size:
            # Keep only the latest project IDs
            sent_projects_list = list(self.sent_projects)
            sent_projects_list.sort(reverse=True)
            self.sent_projects.clear()
            self.sent_projects.update(sent_projects_list[:keep_size])
            logger.info(f"Cleaned up sent projects, kept {keep_size} latest")
    
    def get_min_user_interval(self) -> int:
        """Get minimum interval among all active users."""
        if not self.active_users:
            return config.DEFAULT_CHECK_INTERVAL
        
        return min([self.user_intervals.get(user_id, config.DEFAULT_CHECK_INTERVAL) 
                   for user_id in self.active_users])
    
    def get_filter_description(self, user_id: int) -> str:
        """Get a human-readable description of the user's filters."""
        filters = self.get_user_filters(user_id)
        
        if not filters:
            return "без фільтрів (усі проекти)"
        
        descriptions = []
        
        for key, value in filters.items():
            # Тимчасово відключено опис фільтра only_my_skills
            # if key == "only_my_skills" and value == "1":
            #     descriptions.append("проекти за моїми навичками (з додатковою перевіркою)")
            if key == "skill_id":
                descriptions.append(f"навички [{value}]")
            elif key == "employer_id":
                descriptions.append(f"роботодавець #{value}")
            elif key == "only_for_plus" and value == "1":
                descriptions.append("тільки для Plus-профілів")
        
        return ", ".join(descriptions)
    
    def get_stats(self) -> Dict[str, int]:
        """Get user manager statistics."""
        return {
            "active_users": len(self.active_users),
            "total_users": len(self.user_intervals),
            "sent_projects": len(self.sent_projects)
        }


# Global user manager instance
user_manager = UserManager()