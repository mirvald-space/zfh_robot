"""
User state management.

Manages user states, filters, intervals and sent projects.
Uses MongoDB for persistent storage.
"""

import logging
from typing import Dict, Set, List, Any, Optional
import asyncio

import config
from src.utils.db_manager import db_manager

logger = logging.getLogger(__name__)


class UserManager:
    """Manages user states and settings."""
    
    def __init__(self):
        """Initialize user manager."""
        self.active_users: Set[int] = set()
        self.user_filters: Dict[int, Dict[str, str]] = {}
        self.user_intervals: Dict[int, int] = {}
        self.sent_projects: Set[int] = set()
        self._loaded = False
        
    async def load_data_from_db(self) -> None:
        """Load all user data from database."""
        if self._loaded:
            return
            
        try:
            # Ensure connection to database
            if db_manager.db is None:
                await db_manager.connect()
            
            # Load all users
            users = await db_manager.get_all_users()
            
            for user in users:
                user_id = user.get('user_id')
                
                # Check if user is active
                if user.get('active', False):
                    self.active_users.add(user_id)
                
                # Get user filters
                if 'filters' in user:
                    self.user_filters[user_id] = user['filters']
                
                # Get user interval
                if 'interval' in user:
                    self.user_intervals[user_id] = user['interval']
            
            # Load sent projects
            if db_manager.db is not None:
                projects_cursor = db_manager.db.sent_projects.find()
                async for project in projects_cursor:
                    self.sent_projects.add(project['project_id'])
                
            logger.info(f"Loaded {len(self.active_users)} active users, {len(self.sent_projects)} sent projects")
            self._loaded = True
            
        except Exception as e:
            logger.error(f"Error loading data from database: {e}")
    
    async def save_user_to_db(self, user_id: int, user_data: Dict[str, Any]) -> None:
        """Save user data to database."""
        try:
            await db_manager.add_user(user_data)
            
        except Exception as e:
            logger.error(f"Error saving user {user_id} to database: {e}")
    
    async def activate_user(self, user_id: int, user_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Activate notifications for user.
        
        Args:
            user_id: Telegram user ID
            user_info: Optional additional user information (name, username, etc.)
        """
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        self.active_users.add(user_id)
        
        # Set default interval if not set
        if user_id not in self.user_intervals:
            self.user_intervals[user_id] = config.DEFAULT_CHECK_INTERVAL
        
        # Set empty filter if not set
        if user_id not in self.user_filters:
            self.user_filters[user_id] = {}
        
        # Prepare user data for database
        user_data = {
            'user_id': user_id,
            'active': True,
            'interval': self.user_intervals.get(user_id, config.DEFAULT_CHECK_INTERVAL),
            'filters': self.user_filters.get(user_id, {})
        }
        
        # Add additional user information if provided
        if user_info:
            user_data.update(user_info)
        
        # Save to database
        await self.save_user_to_db(user_id, user_data)
        
        logger.info(f"User {user_id} activated, username: {user_info.get('username') if user_info else 'unknown'}")
    
    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate notifications for user. Returns True if user was active."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        if user_id in self.active_users:
            self.active_users.remove(user_id)
            
            # Update in database
            await db_manager.update_user(user_id, {'active': False})
            
            logger.info(f"User {user_id} deactivated")
            return True
        return False
    
    def is_user_active(self, user_id: int) -> bool:
        """Check if user is active."""
        return user_id in self.active_users
    
    async def set_user_interval(self, user_id: int, interval: int) -> None:
        """Set check interval for user."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        # Validate interval
        if interval < config.MIN_CHECK_INTERVAL:
            interval = config.MIN_CHECK_INTERVAL
        elif interval > config.MAX_CHECK_INTERVAL:
            interval = config.MAX_CHECK_INTERVAL
        
        self.user_intervals[user_id] = interval
        
        # Update in database
        await db_manager.update_user(user_id, {'interval': interval})
        
        logger.info(f"User {user_id} interval set to {interval}s")
    
    def get_user_interval(self, user_id: int) -> int:
        """Get check interval for user."""
        return self.user_intervals.get(user_id, config.DEFAULT_CHECK_INTERVAL)
    
    async def set_user_filters(self, user_id: int, filters: Dict[str, str]) -> None:
        """Set filters for user."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        self.user_filters[user_id] = filters.copy()
        
        # Update in database
        await db_manager.update_user(user_id, {'filters': filters})
        
        logger.info(f"User {user_id} filters updated: {filters}")
    
    def get_user_filters(self, user_id: int) -> Dict[str, str]:
        """Get filters for user."""
        return self.user_filters.get(user_id, {})
    
    async def clear_user_filters(self, user_id: int) -> None:
        """Clear all filters for user."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        self.user_filters[user_id] = {}
        
        # Update in database
        await db_manager.update_user(user_id, {'filters': {}})
        
        logger.info(f"User {user_id} filters cleared")
    
    async def add_sent_project(self, project_id: int) -> None:
        """Mark project as sent."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        self.sent_projects.add(project_id)
        
        # Update in database
        await db_manager.add_sent_project(project_id)
    
    def is_project_sent(self, project_id: int) -> bool:
        """Check if project was already sent."""
        return project_id in self.sent_projects
    
    async def cleanup_sent_projects(self, max_size: int = 1000, keep_size: int = 500) -> None:
        """Clean up sent projects if list gets too large."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
            
        if len(self.sent_projects) > max_size:
            # Keep only the latest project IDs
            sent_projects_list = list(self.sent_projects)
            sent_projects_list.sort(reverse=True)
            self.sent_projects.clear()
            self.sent_projects.update(sent_projects_list[:keep_size])
            
            # Clean up in database
            await db_manager.cleanup_sent_projects(keep_size)
            
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
    
    async def get_stats(self) -> Dict[str, int]:
        """Get user manager statistics."""
        # Ensure data is loaded
        if not self._loaded:
            await self.load_data_from_db()
        
        # Get basic stats
        stats = {
            "active_users": len(self.active_users),
            "total_users": len(self.user_intervals),
            "sent_projects": len(self.sent_projects)
        }
        
        # Try to get additional stats from database
        try:
            if db_manager.db is not None:
                # Get count of new users in the last 24 hours
                import datetime
                yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
                new_users_count = await db_manager.db.users.count_documents({
                    "created_at": {"$gte": yesterday}
                })
                stats["new_users_24h"] = new_users_count
        except Exception as e:
            logger.error(f"Error getting additional stats: {e}")
        
        return stats


# Global user manager instance
user_manager = UserManager()