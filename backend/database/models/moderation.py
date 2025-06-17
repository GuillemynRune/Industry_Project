# backend/database/models/moderation.py
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..connection import mongodb

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
        key_symptoms: List[str],
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Submit story for moderation review"""
        
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
            "embedding": embedding, 
            "status": "pending_review",
            "created_at": datetime.utcnow(),
            "approved_by": None,
            "approved_at": None
        }
        
        result = await mongodb.database.pending_stories.insert_one(story_doc)
        return {
            "success": True,
            "message": "Story submitted for review",
            "story_id": str(result.inserted_id),
            "estimated_review_time": "24-48 hours"
        }
    
    @staticmethod
    async def get_pending_stories(limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending stories for moderation"""
        cursor = mongodb.database.pending_stories.find(
            {"status": "pending_review"}
        ).limit(limit).sort("created_at", 1)
        
        stories = []
        async for story in cursor:
            story["id"] = str(story["_id"])
            story.pop("embedding", None)
            del story["_id"]
            stories.append(story)
        
        return stories