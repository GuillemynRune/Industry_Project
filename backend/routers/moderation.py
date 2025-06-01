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

# Models
class RejectAction(BaseModel):
    reason: Optional[str] = "Does not meet community guidelines"

def require_moderator(current_user: dict = Depends(get_current_active_user)):
    """Require moderator or admin role"""
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user

@router.get("/pending")
async def get_pending_stories(
    current_user: dict = Depends(require_moderator),
    limit: int = 20
):
    """Get stories pending moderation"""
    pending_stories = await ModerationDatabase.get_pending_stories(limit=limit)
    return {
        "success": True,
        "pending_stories": pending_stories,
        "count": len(pending_stories)
    }
    
@router.get("/story/{story_id}")
async def get_story_details(
    story_id: str,
    current_user: dict = Depends(require_moderator)
):
    """Get story details for moderation"""
    story = await mongodb.database.pending_stories.find_one({"_id": ObjectId(story_id)})
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story["_id"] = str(story["_id"])
    return {"success": True, "story": story}
    
@router.post("/approve/{story_id}")
async def approve_story(
    story_id: str,
    current_user: dict = Depends(require_moderator)
):
    """Approve and publish story"""
    story = await mongodb.database.pending_stories.find_one({"_id": ObjectId(story_id)})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Move to approved collection
    approved_story = {
        **story,
        "status": "approved",
        "approved_by": current_user["email"],
        "approved_at": datetime.utcnow(),
    }

    await mongodb.database.approved_stories.insert_one(approved_story)
    await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
    
    return {
        "success": True,
        "message": "✅ Story approved and published"
    }

@router.post("/reject/{story_id}")
async def reject_story(
    story_id: str,
    action: RejectAction,
    current_user: dict = Depends(require_moderator)
):
    """Reject story (delete without storing)"""
    result = await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Story not found")
    
    logger.info(f"Story {story_id} rejected by {current_user['email']}: {action.reason}")
    
    return {
        "success": True,
        "message": "Story rejected and removed from queue"
    }