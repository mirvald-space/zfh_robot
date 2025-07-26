"""
Database manager.

Handles database connections and CRUD operations.
"""

import logging
import datetime
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles database operations."""
    
    def __init__(self):
        """Initialize database manager."""
        self.client = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """
        Connect to MongoDB database.
        
        Creates a connection to MongoDB using the URI from config.
        """
        try:
            # Create client
            self.client = AsyncIOMotorClient(config.MONGO_URI)
            
            # Get database
            self.db = self.client[config.MONGO_DB_NAME]
            
            logger.info(f"Connected to MongoDB: {config.MONGO_DB_NAME}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close MongoDB connection.
        """
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed")
    
    async def add_user(self, user_data: Dict[str, Any]) -> str:
        """
        Add user to database or update if exists.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            User ID
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        user_id = user_data.get('user_id')
        
        if not user_id:
            logger.error("User data is missing user_id")
            return ""
            
        # Check if user exists
        existing_user = await collection.find_one({"user_id": user_id})
        
        if existing_user:
            # Сохраняем список отправленных проектов, если он существует
            if 'sent_projects' in existing_user and 'sent_projects' not in user_data:
                user_data['sent_projects'] = existing_user['sent_projects']
                
            # Update existing user - don't modify created_at
            await collection.update_one(
                {"user_id": user_id},
                {"$set": user_data}
            )
            logger.info(f"Updated user {user_id} in database")
        else:
            # Insert new user with created_at timestamp and empty sent_projects array
            user_data["created_at"] = datetime.datetime.now()
            if 'sent_projects' not in user_data:
                user_data['sent_projects'] = []
            await collection.insert_one(user_data)
            logger.info(f"Added user {user_id} to database with creation timestamp")
        
        return str(user_id)
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user from database by ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User document or None if not found
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        user = await collection.find_one({"user_id": user_id})
        
        return user
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Update user in database.
        
        Args:
            user_id: Telegram user ID
            update_data: Data to update
            
        Returns:
            True if user was updated, False otherwise
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        # Add last_updated field
        update_data["last_updated"] = datetime.datetime.now()
        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated user {user_id} in database")
            return True
            
        logger.warning(f"User {user_id} not found for update")
        return False
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user from database.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user was deleted, False otherwise
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        result = await collection.delete_one({"user_id": user_id})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted user {user_id} from database")
            return True
        
        logger.warning(f"User {user_id} not found for deletion")
        return False
    
    async def get_all_active_users(self) -> List[Dict[str, Any]]:
        """
        Get all active users from database.
        
        Returns:
            List of user documents with active=True
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        cursor = collection.find({"active": True})
        
        users = []
        async for user in cursor:
            users.append(user)
        
        return users
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from database.
        
        Returns:
            List of all user documents
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        cursor = collection.find()
        
        users = []
        async for user in cursor:
            users.append(user)
        
        return users
    
    async def add_sent_project(self, project_id: int, user_id: int) -> None:
        """
        Add project to user's sent_projects list.
        
        Args:
            project_id: Freelancehunt project ID
            user_id: Telegram user ID who received the project
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        
        # Добавляем проект в массив sent_projects, если такого проекта еще нет
        await collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"sent_projects": project_id}}
        )
        
        logger.info(f"Project {project_id} added to sent projects for user {user_id}")
    
    async def is_project_sent(self, project_id: int, user_id: int) -> bool:
        """
        Check if project was already sent to specific user.
        
        Args:
            project_id: Freelancehunt project ID
            user_id: Telegram user ID
            
        Returns:
            True if project was sent to user, False otherwise
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        result = await collection.find_one({
            "user_id": user_id,
            "sent_projects": project_id
        })
        
        return result is not None
    
    async def cleanup_user_sent_projects(self, user_id: int, keep_count: int = 500) -> None:
        """
        Clean up old sent projects for a user, keeping only the newest ones.
        
        Args:
            user_id: Telegram user ID
            keep_count: Number of most recent projects to keep
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        
        # Get user document
        user = await collection.find_one({"user_id": user_id})
        if not user or "sent_projects" not in user:
            return
            
        sent_projects = user.get("sent_projects", [])
        
        # If there are too many projects, keep only the newest ones
        # (assuming newer projects have higher IDs)
        if len(sent_projects) > keep_count:
            # Sort by ID in descending order and keep the most recent ones
            sent_projects.sort(reverse=True)
            new_sent_projects = sent_projects[:keep_count]
            
            # Update the user document
            await collection.update_one(
                {"user_id": user_id},
                {"$set": {"sent_projects": new_sent_projects}}
            )
            
            logger.info(f"Cleaned up sent projects for user {user_id}, kept {keep_count} most recent")


# Global database manager instance
db_manager = DatabaseManager() 