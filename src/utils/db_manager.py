"""
MongoDB database manager.

Provides functionality for database operations and connection management.
"""

import logging
import datetime
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """MongoDB database manager."""
    
    def __init__(self):
        """Initialize database manager."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self) -> None:
        """Connect to MongoDB database."""
        try:
            # Create MongoDB client
            self.client = AsyncIOMotorClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Set database
            self.db = self.client[config.MONGO_DB_NAME]
            
            logger.info(f"Connected to MongoDB: {config.MONGO_DB_NAME}")
            
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            self.client = None
            self.db = None
            raise
    
    async def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    async def add_user(self, user_data: Dict[str, Any]) -> str:
        """
        Add a new user to the database or update if exists.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            User ID as string
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.users
        
        # Ensure user_id is present
        if 'user_id' not in user_data:
            raise ValueError("user_id is required")
        
        user_id = user_data['user_id']
        
        # Try to find user first
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
        Get user from database by user_id.
        
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
        Update user document with new data.
        
        Args:
            user_id: Telegram user ID
            update_data: Data to update
            
        Returns:
            True if successful, False otherwise
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
        
        logger.warning(f"User {user_id} update had no effect")
        return False
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user from database.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if successful, False if user not found
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
    
    async def add_sent_project(self, project_id: int) -> None:
        """
        Add project to sent projects collection.
        
        Args:
            project_id: Freelancehunt project ID
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.sent_projects
        
        # Use upsert to ensure we don't have duplicates
        await collection.update_one(
            {"project_id": project_id},
            {"$set": {"project_id": project_id, "timestamp": datetime.datetime.now()}},
            upsert=True
        )
    
    async def is_project_sent(self, project_id: int) -> bool:
        """
        Check if project was already sent.
        
        Args:
            project_id: Freelancehunt project ID
            
        Returns:
            True if project was sent, False otherwise
        """
        if self.db is None:
            await self.connect()
        
        collection = self.db.sent_projects
        result = await collection.find_one({"project_id": project_id})
        
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


# Global database manager instance
db_manager = DatabaseManager() 