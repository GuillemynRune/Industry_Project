import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
from database.connection import mongodb

logger = logging.getLogger(__name__)

class ModerationDatabase:
    """Content moderation database operations"""
    
    @staticmethod
    async def submit_story_for_review(
        user_id: str,
        author_name: str,
        challenge: str,
        experience: str,
        solution: str,
        advice: str,
        generated_story: str,
        model_used: str,
        key_symptoms: List[str]
    ) -> Dict[str, Any]:
        """Submit story for moderation review"""
        try:
            story_doc = {
                "content_type": "story",
                "user_id": user_id,
                "author_name": author_name,
                "challenge": challenge,
                "experience": experience,
                "solution": solution,
                "advice": advice,
                "generated_story": generated_story,
                "model_used": model_used,
                "key_symptoms": key_symptoms,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "reviewed_at": None,
                "reviewer_id": None,
                "review_notes": None
            }
            
            result = await mongodb.database.pending_stories.insert_one(story_doc)
            
            return {
                "success": True,
                "message": "Story submitted for review",
                "story_id": str(result.inserted_id),
                "estimated_review_time": "24-48 hours"
            }
            
        except Exception as e:
            logger.error(f"Error submitting story for review: {e}")
            return {"success": False, "message": "Failed to submit story"}
    
    @staticmethod
    async def submit_for_moderation(
        content_type: str,
        content_id: str,
        content_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit content for moderation"""
        try:
            moderation_doc = {
                "content_type": content_type,  # 'story', 'symptom', etc.
                "content_id": content_id,
                "content_data": content_data,
                "user_id": user_id,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "reviewed_at": None,
                "reviewer_id": None,
                "review_notes": None
            }
            
            result = await mongodb.database.pending_moderation.insert_one(moderation_doc)
            
            return {
                "success": True,
                "message": "Content submitted for moderation",
                "moderation_id": str(result.inserted_id)
            }
            
        except Exception as e:
            logger.error(f"Error submitting for moderation: {e}")
            return {"success": False, "message": "Failed to submit for moderation"}
    
    @staticmethod
    async def get_pending_stories(limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending stories for moderation"""
        try:
            cursor = mongodb.database.pending_stories.find(
                {"status": "pending"}
            ).limit(limit).sort("created_at", 1)
            
            stories = []
            async for story in cursor:
                story["id"] = str(story["_id"])
                del story["_id"]
                stories.append(story)
            
            return stories
        except Exception as e:
            logger.error(f"Error getting pending stories: {e}")
            return []
    
    @staticmethod
    async def get_pending_content(limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending moderation content"""
        try:
            cursor = mongodb.database.pending_moderation.find(
                {"status": "pending"}
            ).limit(limit).sort("created_at", 1)
            
            content = []
            async for item in cursor:
                item["id"] = str(item["_id"])
                del item["_id"]
                content.append(item)
            
            return content
        except Exception as e:
            logger.error(f"Error getting pending content: {e}")
            return []
    
    @staticmethod
    async def approve_content(moderation_id: str, reviewer_id: str, notes: Optional[str] = None) -> bool:
        """Approve moderated content"""
        try:
            result = await mongodb.database.pending_moderation.update_one(
                {"_id": ObjectId(moderation_id)},
                {
                    "$set": {
                        "status": "approved",
                        "reviewed_at": datetime.utcnow(),
                        "reviewer_id": reviewer_id,
                        "review_notes": notes
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error approving content: {e}")
            return False
    
    @staticmethod
    async def reject_content(moderation_id: str, reviewer_id: str, notes: str) -> bool:
        """Reject moderated content"""
        try:
            result = await mongodb.database.pending_moderation.update_one(
                {"_id": ObjectId(moderation_id)},
                {
                    "$set": {
                        "status": "rejected",
                        "reviewed_at": datetime.utcnow(),
                        "reviewer_id": reviewer_id,
                        "review_notes": notes
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error rejecting content: {e}")
            return False
    
    @staticmethod
    async def get_moderation_stats() -> Dict[str, Any]:
        """Get moderation statistics"""
        try:
            pending_count = await mongodb.database.pending_moderation.count_documents({"status": "pending"})
            approved_count = await mongodb.database.pending_moderation.count_documents({"status": "approved"})
            rejected_count = await mongodb.database.pending_moderation.count_documents({"status": "rejected"})
            
            return {
                "pending": pending_count,
                "approved": approved_count,
                "rejected": rejected_count,
                "total": pending_count + approved_count + rejected_count
            }
        except Exception as e:
            logger.error(f"Error getting moderation stats: {e}")
            return {}