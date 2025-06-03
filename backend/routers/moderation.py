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
    limit: int = 4,
    offset: int = 0
):
    """Get stories pending moderation with pagination"""
    
    # Get total count
    total_pending = await mongodb.database.pending_stories.count_documents({"status": "pending_review"})
    
    # Get limited stories
    cursor = mongodb.database.pending_stories.find(
        {"status": "pending_review"}
    ).sort("created_at", 1).skip(offset).limit(limit)
    
    stories = []
    async for story in cursor:
        story["id"] = str(story["_id"])
        del story["_id"]
        stories.append(story)
    
    return {
        "success": True,
        "pending_stories": stories,
        "total_count": total_pending,
        "displayed_count": len(stories),
        "has_more": (offset + len(stories)) < total_pending
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

@router.get("/stats")
async def get_moderation_stats(current_user: dict = Depends(require_moderator)):
    """Get real-time moderation statistics"""
    total_pending = await mongodb.database.pending_stories.count_documents({"status": "pending_review"})
    total_approved = await mongodb.database.approved_stories.count_documents({})
    
    return {
        "success": True,
        "total_pending": total_pending,
        "total_approved": total_approved
    }