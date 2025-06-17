import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bson import ObjectId
from ..connection import mongodb

logger = logging.getLogger(__name__)

class SavedStoriesDatabase:
    """Saved stories database operations"""
    
    @staticmethod
    async def save_story(user_id: str, story_id: str) -> Dict[str, Any]:
        """Save a story for a user"""
        try:
            # Check if story is already saved
            existing = await mongodb.database.saved_stories.find_one({
                "user_id": user_id,
                "story_id": story_id
            })
            
            if existing:
                return {
                    "success": False,
                    "message": "Story already saved",
                    "already_saved": True
                }
            
            # Create save record
            save_doc = {
                "user_id": user_id,
                "story_id": story_id,
                "saved_at": datetime.utcnow()
            }
            
            result = await mongodb.database.saved_stories.insert_one(save_doc)
            
            logger.info(f"Story {story_id} saved by user {user_id}")
            
            return {
                "success": True,
                "message": "Story saved successfully",
                "save_id": str(result.inserted_id)
            }
            
        except Exception as e:
            logger.error(f"Error saving story: {e}")
            return {
                "success": False,
                "message": "Failed to save story",
                "error": str(e)
            }
    
    @staticmethod
    async def unsave_story(user_id: str, story_id: str) -> Dict[str, Any]:
        """Remove a saved story for a user"""
        try:
            result = await mongodb.database.saved_stories.delete_one({
                "user_id": user_id,
                "story_id": story_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Story {story_id} unsaved by user {user_id}")
                return {
                    "success": True,
                    "message": "Story removed from saved stories"
                }
            else:
                return {
                    "success": False,
                    "message": "Story was not saved",
                    "not_found": True
                }
                
        except Exception as e:
            logger.error(f"Error unsaving story: {e}")
            return {
                "success": False,
                "message": "Failed to remove saved story",
                "error": str(e)
            }
    
    @staticmethod
    async def get_saved_stories(user_id: str, limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """Get user's saved stories with full story details"""
        try:
            # Aggregation pipeline to join saved stories with actual story content
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$sort": {"saved_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
                {
                    "$lookup": {
                        "from": "approved_stories",
                        "let": {"story_id": {"$toObjectId": "$story_id"}},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$_id", "$$story_id"]}}}
                        ],
                        "as": "story"
                    }
                },
                {"$unwind": "$story"},
                {
                    "$project": {
                        "saved_at": 1,
                        "story_id": 1,
                        "story._id": 1,
                        "story.challenge": 1,
                        "story.experience": 1,
                        "story.solution": 1,
                        "story.advice": 1,
                        "story.generated_story": 1,
                        "story.author_name": 1,
                        "story.created_at": 1,
                        "story.key_symptoms": 1
                    }
                }
            ]
            
            cursor = mongodb.database.saved_stories.aggregate(pipeline)
            saved_stories = []
            
            async for doc in cursor:
                story = doc["story"]
                story["id"] = str(story["_id"])
                story["saved_at"] = doc["saved_at"]
                del story["_id"]
                saved_stories.append(story)
            
            # Get total count
            total_count = await mongodb.database.saved_stories.count_documents({"user_id": user_id})
            
            return {
                "success": True,
                "saved_stories": saved_stories,
                "total_count": total_count,
                "displayed_count": len(saved_stories)
            }
            
        except Exception as e:
            logger.error(f"Error getting saved stories: {e}")
            return {
                "success": False,
                "message": "Failed to retrieve saved stories",
                "error": str(e),
                "saved_stories": [],
                "total_count": 0
            }
    
    @staticmethod
    async def is_story_saved(user_id: str, story_id: str) -> bool:
        """Check if a story is saved by user"""
        try:
            existing = await mongodb.database.saved_stories.find_one({
                "user_id": user_id,
                "story_id": story_id
            })
            return existing is not None
        except Exception as e:
            logger.error(f"Error checking if story is saved: {e}")
            return False
    
    @staticmethod
    async def get_saved_stories_stats(user_id: str) -> Dict[str, Any]:
        """Get statistics about user's saved stories"""
        try:
            total_saved = await mongodb.database.saved_stories.count_documents({"user_id": user_id})
            
            # Get recent saves (last 7 days)
            recent_date = datetime.utcnow() - timedelta(days=7)
            recent_saved = await mongodb.database.saved_stories.count_documents({
                "user_id": user_id,
                "saved_at": {"$gte": recent_date}
            })
            
            return {
                "total_saved": total_saved,
                "recent_saved": recent_saved
            }
            
        except Exception as e:
            logger.error(f"Error getting saved stories stats: {e}")
            return {
                "total_saved": 0,
                "recent_saved": 0
            }
    
    @staticmethod
    async def cleanup_orphaned_saves():
        """Remove saves for stories that no longer exist"""
        try:
            # Find all saved story IDs
            saved_story_ids = []
            async for doc in mongodb.database.saved_stories.find({}, {"story_id": 1}):
                try:
                    saved_story_ids.append(ObjectId(doc["story_id"]))
                except:
                    # Invalid ObjectId, will be cleaned up
                    pass
            
            # Find which stories actually exist
            existing_stories = []
            async for doc in mongodb.database.approved_stories.find(
                {"_id": {"$in": saved_story_ids}}, 
                {"_id": 1}
            ):
                existing_stories.append(str(doc["_id"]))
            
            # Remove saves for non-existent stories
            result = await mongodb.database.saved_stories.delete_many({
                "story_id": {"$nin": existing_stories}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} orphaned saved stories")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned saves: {e}")
            return 0