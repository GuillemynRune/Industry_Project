from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.models.moderation import ModerationDatabase
from database.connection import mongodb
from routers.auth import get_current_active_user
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/moderation", tags=["moderation"])

# Pydantic models
class ModerationAction(BaseModel):
    notes: Optional[str] = ""

class RejectAction(BaseModel):
    reason: Optional[str] = "Does not meet community guidelines"

@router.get("/pending")
async def get_pending_stories(
    current_user: dict = Depends(get_current_active_user),
    limit: int = 20
):
    """Get stories pending moderation (moderators only)"""
    
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        pending_stories = await ModerationDatabase.get_pending_stories(limit=limit)
        
        return {
            "success": True,
            "pending_stories": pending_stories,
            "count": len(pending_stories)
        }
    except Exception as e:
        logger.error(f"Error getting pending stories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pending stories")
    
@router.get("/story/{story_id}")
async def get_story_details(
    story_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get individual story details for moderation"""
    
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        story = await mongodb.database.pending_stories.find_one({"_id": ObjectId(story_id)})
        
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        story["_id"] = str(story["_id"])
        
        return {
            "success": True,
            "story": story
        }
        
    except Exception as e:
        logger.error(f"Error fetching story details: {e}")
        raise HTTPException(status_code=500, detail="Error fetching story details")
    
@router.post("/approve/{story_id}")
async def approve_story(
    story_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Approve a pending story and move it to approved_stories"""
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    story = await mongodb.database.pending_stories.find_one({"_id": ObjectId(story_id)})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    approved_story = {
        **story,
        "status": "approved",
        "approved_by": current_user["email"],
        "approved_at": datetime.utcnow(),
    }

    try:
        await mongodb.database.approved_stories.insert_one(approved_story)
        await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
        return {
            "success": True,
            "message": "✅ Story approved and published"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve story: {str(e)}")

@router.post("/reject/{story_id}")
async def reject_story(
    story_id: str,
    action: RejectAction,
    current_user: dict = Depends(get_current_active_user)
):
    """Reject a pending story (delete without storing)"""
    
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Check if story exists
        pending_story = await mongodb.database.pending_stories.find_one(
            {"_id": ObjectId(story_id)}
        )
        
        if not pending_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Simply delete from pending - no storage of rejected stories
        await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
        
        logger.info(f"Story {story_id} rejected and deleted by {current_user['email']}")
        
        return {
            "success": True,
            "message": "Story rejected and removed from queue"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting story: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject story")