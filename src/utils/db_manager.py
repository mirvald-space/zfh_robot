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
            # Update existing user - don't modify created_at
            await collection.update_one(
                {"user_id": user_id},
                {"$set": user_data}
            )
            logger.info(f"Updated user {user_id} in database")
        else:
            # Insert new user with created_at timestamp
            user_data["created_at"] = datetime.datetime.now()
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
        Add project to sent projects collection with user ID.
        
        Args:
            project_id: Freelancehunt project ID
            user_id: Telegram user ID who received the project
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.sent_projects
        
        # Найдем запись о проекте
        project_doc = await collection.find_one({"project_id": project_id})
        
        if project_doc:
            # Если запись существует, добавляем user_id в список, если его еще нет
            user_ids = project_doc.get("user_ids", [])
            if user_id not in user_ids:
                user_ids.append(user_id)
                await collection.update_one(
                    {"project_id": project_id},
                    {"$set": {"user_ids": user_ids, "last_updated": datetime.datetime.now()}}
                )
        else:
            # Если записи не существует, создаем новую с user_id в списке
            await collection.insert_one({
                "project_id": project_id,
                "user_ids": [user_id],
                "timestamp": datetime.datetime.now(),
                "last_updated": datetime.datetime.now()
            })
    
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
        
        collection = self.db.sent_projects
        result = await collection.find_one({
            "project_id": project_id,
            "user_ids": {"$in": [user_id]}
        })
        
        return result is not None
    
    async def cleanup_sent_projects(self, limit: int = 1000) -> None:
        """
        Clean up old sent projects, keeping only the newest ones.
        
        Args:
            limit: Number of projects to keep
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.sent_projects
        
        # Count total documents
        count = await collection.count_documents({})
        
        if count > limit:
            # Get all project IDs sorted by project_id (newer IDs are larger)
            cursor = collection.find().sort("project_id", 1)
            
            # Calculate how many to delete
            to_delete = count - limit
            
            # Get IDs to delete
            delete_ids = []
            async for doc in cursor.limit(to_delete):
                delete_ids.append(doc["project_id"])
            
            # Delete old projects
            if delete_ids:
                await collection.delete_many({"project_id": {"$in": delete_ids}})
                logger.info(f"Cleaned up {len(delete_ids)} old sent projects")
                
    async def cleanup_user_sent_projects(self, user_id: int, project_ids: List[int]) -> None:
        """
        Remove user from list of recipients for specified projects.
        
        Args:
            user_id: Telegram user ID
            project_ids: List of project IDs to clean up
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.sent_projects
        
        # Удаляем пользователя из списка получателей проектов
        await collection.update_many(
            {"project_id": {"$in": project_ids}, "user_ids": user_id},
            {"$pull": {"user_ids": user_id}}
        )
        
        # Удаляем проекты, у которых не осталось получателей
        await collection.delete_many({"user_ids": {"$size": 0}})
        
        logger.info(f"Cleaned up {len(project_ids)} sent projects for user {user_id}")


# Global database manager instance
db_manager = DatabaseManager() 