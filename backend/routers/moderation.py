from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database.models.moderation import ModerationDatabase
from database.connection import mongodb
from routers.auth import get_current_active_user
from bson import ObjectId
from datetime import datetime
import logging
import traceback

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

@router.post("/reject/{story_id}")
async def reject_story(
    story_id: str,
    action: RejectAction,
    current_user: dict = Depends(require_moderator)
):
    """Reject story and move to rejected collection"""
    try:
        story = await mongodb.database.pending_stories.find_one({"_id": ObjectId(story_id)})
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Move to rejected collection with rejection info
        rejected_story = {
            **story,
            "status": "rejected",
            "rejected_by": current_user["email"],
            "rejected_at": datetime.utcnow(),
            "rejection_reason": action.reason or "Does not meet community guidelines"
        }

        # DEBUG: Log what we're trying to insert
        logger.info(f"Rejecting story {story_id} by {current_user['email']}")
        logger.info(f"Rejected story user_id type: {type(rejected_story.get('user_id'))}")
        logger.info(f"Rejected story user_id value: {rejected_story.get('user_id')}")

        # Insert into rejected collection and remove from pending
        try:
            result = await mongodb.database.rejected_stories.insert_one(rejected_story)
            logger.info(f"Successfully inserted rejected story with ID: {result.inserted_id}")
            
            # Only delete from pending if rejection insert succeeded
            await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
            logger.info(f"Successfully deleted story {story_id} from pending_stories")
            
        except Exception as db_error:
            logger.error(f"Database error during rejection: {db_error}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        logger.info(f"Story {story_id} rejected by {current_user['email']}: {action.reason}")
        
        return {
            "success": True,
            "message": "Story rejected and moved to rejected collection"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error rejecting story {story_id}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error during rejection")

# Add this debug endpoint to check collections
@router.get("/debug/collections")
async def debug_collections(current_user: dict = Depends(require_moderator)):
    """Debug endpoint to check collections exist"""
    try:
        collections = await mongodb.database.list_collection_names()
        
        # Count documents in each collection
        stats = {}
        for collection_name in ['pending_stories', 'approved_stories', 'rejected_stories']:
            try:
                count = await mongodb.database[collection_name].count_documents({})
                stats[collection_name] = {
                    "exists": collection_name in collections,
                    "count": count
                }
            except Exception as e:
                stats[collection_name] = {
                    "exists": collection_name in collections,
                    "error": str(e)
                }
        
        return {
            "all_collections": collections,
            "story_collections": stats
        }
    except Exception as e:
        logger.error(f"Debug collections error: {e}")
        return {"error": str(e)}