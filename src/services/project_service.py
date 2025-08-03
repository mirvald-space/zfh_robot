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
        
        # Ensure user data is loaded from database
        if not user_manager._loaded:
            await user_manager.load_data_from_db()
        
        logger.info("Starting periodic project monitoring loop")
        
        while self.is_running:
            # Calculate smart interval and wait first
            await self._wait_smart_interval()
            
            try:
                await self._check_projects_for_all_users()
            except Exception as e:
                logger.error(f"Error in project monitoring loop: {e}", exc_info=True)
    
    def stop_monitoring(self) -> None:
        """Stop the project monitoring loop."""
        self.is_running = False
        logger.info("Stopping project monitoring service")
    
    async def _check_projects_for_all_users(self) -> None:
        """Check for new projects for all active users."""
        # Skip if there are no active users
        active_users = user_manager.active_users
        active_users_count = len(active_users)
        
        logger.info(f"Found {active_users_count} active users to notify about new projects")
        
        if not active_users:
            logger.info("No active users found, waiting 10s before next check")
            await asyncio.sleep(10)  # Wait for users to become active
            return
        
        # Check for each active user with their filters
        for user_id in active_users.copy():  # Copy to avoid modification during iteration
            try:
                await self._check_projects_for_user(user_id)
            except Exception as e:
                logger.error(f"Error checking projects for user {user_id}: {e}", exc_info=True)
        
        # Clean up sent projects if list gets too large
        await user_manager.cleanup_sent_projects()
    
    async def _check_projects_for_user(self, user_id: int) -> None:
        """Check and send new projects for a specific user."""
        user_filters = user_manager.get_user_filters(user_id)
        logger.info(f"Checking projects for user {user_id} with filters: {user_filters}")
        
        # Get projects from API
        projects = await api_client.get_projects(user_filters)
        if not projects:
            # logger.warning(f"No projects received from API for user {user_id}")
            return
        
        logger.info(f"Processing {len(projects)} projects for user {user_id}")
        
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
        
        logger.info(f"Processing project {project_id} for user {user_id}")
        
        # Check if project should be processed
        if not project_checker.should_process_project(
            project, user_filters, user_skills, user_id, user_manager.user_sent_projects
        ):
            logger.info(f"Project {project_id} not suitable for user {user_id}, skipping")
            return
        
        # Mark project as sent to this user
        logger.info(f"Adding project {project_id} to sent projects for user {user_id}")
        await user_manager.add_sent_project(project_id, user_id)
        
        # Format and send message
        # Тимчасово відключено відображення skill_ids оскільки фільтр only_my_skills недоступний
        show_skill_ids = False  # user_filters.get("only_my_skills") == "1"
        message_text, keyboard = message_formatter.format_project_message(project, show_skill_ids)
        
        try:
            logger.info(f"Sending project {project_id} to user {user_id}")
            await self.bot.send_message(
                user_id, 
                message_text, 
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
            logger.info(f"Successfully sent project {project_id} to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}", exc_info=True)
    
    async def _wait_smart_interval(self) -> None:
        """Wait for the calculated smart interval."""
        if not user_manager.active_users:
            logger.debug("No active users, using short interval")
            await asyncio.sleep(10)
            return
        
        min_user_interval = user_manager.get_min_user_interval()
        active_users_count = len(user_manager.active_users)
        
        smart_interval = project_checker.calculate_smart_interval(
            min_user_interval, 
            active_users_count, 
            rate_limiter.remaining
        )
        
        logger.info(f"Waiting {smart_interval}s until next check (min_interval={min_user_interval}s, users={active_users_count}, rate_remaining={rate_limiter.remaining})")
        await asyncio.sleep(smart_interval)


# This will be initialized in main bot file
project_service = None