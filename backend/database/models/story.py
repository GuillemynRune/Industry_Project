import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from database.connection import mongodb

logger = logging.getLogger(__name__)

class StoryDatabase:
    """Recovery story database operations"""
    
    @staticmethod
    async def get_story_by_id(story_id: str) -> Optional[Dict[str, Any]]:
        """Get story by ID from approved stories collection only"""
        try:
            story = await mongodb.database.approved_stories.find_one({"_id": ObjectId(story_id)})
            
            if story:
                story["id"] = str(story["_id"])
                del story["_id"]
            return story
        except Exception as e:
            logger.error(f"Error getting story by ID: {e}")
            return None
    
    @staticmethod
    async def get_recovery_stories(limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """Get approved recovery stories with pagination"""
        try:
            cursor = mongodb.database.approved_stories.find(
                {}
            ).skip(skip).limit(limit).sort("created_at", -1)
            
            stories = []
            async for story in cursor:
                story["id"] = str(story["_id"])
                del story["_id"]
                stories.append(story)
            
            return stories
        except Exception as e:
            logger.error(f"Error getting recovery stories: {e}")
            return []
    
    @staticmethod
    async def search_recovery_stories(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search recovery stories using text search"""
        try:
            cursor = mongodb.database.approved_stories.find(
                {"$text": {"$search": query}}
            ).limit(limit).sort("created_at", -1)
            
            stories = []
            async for story in cursor:
                story["id"] = str(story["_id"])
                del story["_id"]
                stories.append(story)
            
            return stories
        except Exception as e:
            logger.error(f"Error searching stories: {e}")
            return []

    @staticmethod
    async def get_recent_stories(limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent approved stories"""
        try:
            cursor = mongodb.database.approved_stories.find(
                {}
            ).limit(limit).sort("created_at", -1)
            
            stories = []
            async for story in cursor:
                story["id"] = str(story["_id"])
                del story["_id"]
                stories.append(story)
            
            return stories
        except Exception as e:
            logger.error(f"Error getting recent stories: {e}")
            return []
    
    @staticmethod
    async def increment_story_views(story_id: str) -> bool:
        """Increment story view count"""
        try:
            result = await mongodb.database.approved_stories.update_one(
                {"_id": ObjectId(story_id)},
                {"$inc": {"views": 1}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing views: {e}")
            return False
    
    @staticmethod
    async def vote_helpful(story_id: str) -> bool:
        """Vote story as helpful"""
        try:
            result = await mongodb.database.approved_stories.update_one(
                {"_id": ObjectId(story_id)},
                {"$inc": {"helpful_votes": 1}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error voting helpful: {e}")
            return False
    
    @staticmethod
    async def get_database_stats() -> Dict[str, Any]:
        """Get database statistics"""
        try:
            approved_stories = await mongodb.database.approved_stories.count_documents({})
            pending_stories = await mongodb.database.pending_stories.count_documents({})
            total_users = await mongodb.database.users.count_documents({})
            
            return {
                "approved_stories": approved_stories,
                "pending_stories": pending_stories,
                "total_users": total_users
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}