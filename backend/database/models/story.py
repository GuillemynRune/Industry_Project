import logging
from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId
from ..connection import mongodb

logger = logging.getLogger(__name__)

class StoryDatabase:
    """Recovery story database operations"""
    
    @staticmethod
    async def get_story_by_id(story_id: str) -> Dict[str, Any]:
        """Get story by ID from approved stories"""
        story = await mongodb.database.approved_stories.find_one({"_id": ObjectId(story_id)})
        if story:
            story["id"] = str(story["_id"])
            del story["_id"]
        return story
    
    @staticmethod
    async def get_recovery_stories(limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """Get approved recovery stories with pagination"""
        cursor = mongodb.database.approved_stories.find({}).skip(skip).limit(limit).sort("created_at", -1)
        
        stories = []
        async for story in cursor:
            story["id"] = str(story["_id"])
            del story["_id"]
            stories.append(story)
        
        return stories
    
    @staticmethod
    async def search_recovery_stories(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search recovery stories using text search"""
        cursor = mongodb.database.approved_stories.find(
            {"$text": {"$search": query}}
        ).limit(limit).sort("created_at", -1)
        
        stories = []
        async for story in cursor:
            story["id"] = str(story["_id"])
            del story["_id"]
            stories.append(story)
        
        return stories

    @staticmethod
    async def get_database_stats() -> Dict[str, Any]:
        """Get database statistics"""
        try:
            approved_stories = await mongodb.database.approved_stories.count_documents({})
            pending_stories = await mongodb.database.pending_stories.count_documents({})
            total_users = await mongodb.database.users.count_documents({})
            
            return {
                "total_stories": approved_stories,
                "approved_stories": approved_stories,
                "pending_stories": pending_stories,
                "total_users": total_users,
                "database_connected": True
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {
                "total_stories": 0,
                "approved_stories": 0,
                "pending_stories": 0,
                "total_users": 0,
                "database_connected": False
            }