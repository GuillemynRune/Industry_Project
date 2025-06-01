import logging
from datetime import datetime
from typing import Dict, Any, List
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
        key_symptoms: List[str]
    ) -> Dict[str, Any]:
        """Submit story for moderation review"""
        
        story_doc = {
            "user_id": user_id,
            "author_name": author_name,
            "challenge": challenge,
            "experience": experience,
            "solution": solution,
            "advice": advice,
            "generated_story": generated_story,
            "model_used": model_used,
            "key_symptoms": key_symptoms,
            "status": "pending_review",
            "created_at": datetime.utcnow(),
            "risk_level": ModerationDatabase._assess_risk_level(experience, advice)
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
            del story["_id"]
            stories.append(story)
        
        return stories
    
    @staticmethod
    def _assess_risk_level(experience: str, advice: str) -> str:
        """Assess content risk level"""
        combined_text = f"{experience} {advice}".lower()
        
        high_risk = ["suicide", "kill myself", "end it all", "hurt myself", "self harm"]
        medium_risk = ["hopeless", "can't cope", "giving up", "breaking down", "overwhelmed"]
        
        if any(keyword in combined_text for keyword in high_risk):
            return "high"
        elif sum(1 for keyword in medium_risk if keyword in combined_text) >= 2:
            return "medium"
        else:
            return "low"