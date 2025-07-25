"""
Project monitoring service.

Main service that checks for new projects and sends notifications.
"""

import asyncio
import logging

from aiogram import Bot

from src.api.freelancehunt import api_client
from src.api.rate_limiter import rate_limiter
from src.utils.user_manager import user_manager
from src.utils.message_formatter import message_formatter
from src.utils.project_checker import project_checker

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for monitoring and notifying about new projects."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
    
    async def start_monitoring(self) -> None:
        """Start the project monitoring loop."""
        if self.is_running:
            logger.warning("Project monitoring is already running")
            return
        
        self.is_running = True
        logger.info("Starting project monitoring service")
        
        while self.is_running:
            try:
                await self._check_projects_for_all_users()
            except Exception as e:
                logger.error(f"Error in project monitoring loop: {e}")
            
            # Calculate smart interval and wait
            await self._wait_smart_interval()
    
    def stop_monitoring(self) -> None:
        """Stop the project monitoring loop."""
        self.is_running = False
        logger.info("Stopping project monitoring service")
    
    async def _check_projects_for_all_users(self) -> None:
        """Check for new projects for all active users."""
        # Skip if there are no active users
        if not user_manager.active_users:
            await asyncio.sleep(10)  # Wait for users to become active
            return
        
        # Check for each active user with their filters
        for user_id in user_manager.active_users.copy():  # Copy to avoid modification during iteration
            try:
                await self._check_projects_for_user(user_id)
            except Exception as e:
                logger.error(f"Error checking projects for user {user_id}: {e}")
        
        # Clean up sent projects if list gets too large
        user_manager.cleanup_sent_projects()
    
    async def _check_projects_for_user(self, user_id: int) -> None:
        """Check and send new projects for a specific user."""
        user_filters = user_manager.get_user_filters(user_id)
        logger.info(f"Checking projects for user {user_id} with filters: {user_filters}")
        
        # Get projects from API
        projects = await api_client.get_projects(user_filters)
        if not projects:
            return
        
        # Тимчасово відключено отримання навичок користувача
        # оскільки фільтр only_my_skills працює тільки з персональним ключем
        user_skills = []
        # if user_filters.get("only_my_skills") == "1":
        #     user_skills = await api_client.get_user_skills()
        #     logger.info(f"User {user_id} skills: {user_skills}")
        
        # Process projects (newest first)
        for project in reversed(projects):
            await self._process_project_for_user(project, user_id, user_filters, user_skills)
    
    async def _process_project_for_user(self, project: dict, user_id: int, 
                                      user_filters: dict, user_skills: list) -> None:
        """Process a single project for a user."""
        project_id = project.get("id")
        
        # Check if project should be processed
        if not project_checker.should_process_project(
            project, user_filters, user_skills, user_manager.sent_projects
        ):
            return
        
        # Mark project as sent
        user_manager.add_sent_project(project_id)
        
        # Format and send message
        # Тимчасово відключено відображення skill_ids оскільки фільтр only_my_skills недоступний
        show_skill_ids = False  # user_filters.get("only_my_skills") == "1"
        message_text = message_formatter.format_project_message(project, show_skill_ids)
        
        try:
            await self.bot.send_message(user_id, message_text)
            logger.info(f"Sent project {project_id} to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
    
    async def _wait_smart_interval(self) -> None:
        """Wait for the calculated smart interval."""
        if not user_manager.active_users:
            await asyncio.sleep(10)
            return
        
        min_user_interval = user_manager.get_min_user_interval()
        active_users_count = len(user_manager.active_users)
        
        smart_interval = project_checker.calculate_smart_interval(
            min_user_interval, 
            active_users_count, 
            rate_limiter.remaining
        )
        
        logger.debug(f"Waiting {smart_interval}s until next check")
        await asyncio.sleep(smart_interval)


# This will be initialized in main bot file
project_service = None