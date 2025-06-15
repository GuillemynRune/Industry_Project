# This file should be saved as: backend/routers/saved_stories.py

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from database.models.saved_stories import SavedStoriesDatabase
from routers.auth import get_current_active_user
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stories/saved", tags=["saved-stories"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Models
class SaveStoryRequest(BaseModel):
    story_id: str

class SaveStoryResponse(BaseModel):
    success: bool
    message: str
    is_saved: Optional[bool] = None

@router.post("/save", response_model=SaveStoryResponse)
@limiter.limit("30/minute")  # Prevent spam saving
async def save_story(
    request: Request,
    save_request: SaveStoryRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Save a story for the current user"""
    
    if not save_request.story_id.strip():
        raise HTTPException(status_code=400, detail="Story ID is required")
    
    try:
        result = await SavedStoriesDatabase.save_story(
            user_id=current_user["id"],
            story_id=save_request.story_id
        )
        
        if result["success"]:
            return SaveStoryResponse(
                success=True,
                message=result["message"],
                is_saved=True
            )
        else:
            # Handle already saved case
            if result.get("already_saved"):
                return SaveStoryResponse(
                    success=True,
                    message="Story already in your saved collection",
                    is_saved=True
                )
            else:
                raise HTTPException(status_code=500, detail=result["message"])
                
    except Exception as e:
        logger.error(f"Error in save_story endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to save story")

@router.delete("/unsave", response_model=SaveStoryResponse)
@limiter.limit("30/minute")
async def unsave_story(
    request: Request,
    save_request: SaveStoryRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Remove a story from user's saved stories"""
    
    if not save_request.story_id.strip():
        raise HTTPException(status_code=400, detail="Story ID is required")
    
    try:
        result = await SavedStoriesDatabase.unsave_story(
            user_id=current_user["id"],
            story_id=save_request.story_id
        )
        
        if result["success"]:
            return SaveStoryResponse(
                success=True,
                message=result["message"],
                is_saved=False
            )
        else:
            # Handle not found case
            if result.get("not_found"):
                return SaveStoryResponse(
                    success=True,
                    message="Story was not in your saved collection",
                    is_saved=False
                )
            else:
                raise HTTPException(status_code=500, detail=result["message"])
                
    except Exception as e:
        logger.error(f"Error in unsave_story endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove saved story")

@router.post("/toggle", response_model=SaveStoryResponse)
@limiter.limit("30/minute")
async def toggle_save_story(
    request: Request,
    save_request: SaveStoryRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Toggle save status of a story (save if not saved, unsave if saved)"""
    
    if not save_request.story_id.strip():
        raise HTTPException(status_code=400, detail="Story ID is required")
    
    try:
        # Check current status
        is_saved = await SavedStoriesDatabase.is_story_saved(
            user_id=current_user["id"],
            story_id=save_request.story_id
        )
        
        if is_saved:
            # Unsave it
            result = await SavedStoriesDatabase.unsave_story(
                user_id=current_user["id"],
                story_id=save_request.story_id
            )
            return SaveStoryResponse(
                success=True,
                message="Story removed from saved collection",
                is_saved=False
            )
        else:
            # Save it
            result = await SavedStoriesDatabase.save_story(
                user_id=current_user["id"],
                story_id=save_request.story_id
            )
            return SaveStoryResponse(
                success=True,
                message="Story added to saved collection",
                is_saved=True
            )
            
    except Exception as e:
        logger.error(f"Error in toggle_save_story endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle story save status")

@router.get("/list")
async def get_saved_stories(
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    """Get user's saved stories"""
    
    try:
        result = await SavedStoriesDatabase.get_saved_stories(
            user_id=current_user["id"],
            limit=limit,
            skip=skip
        )
        
        if result["success"]:
            return {
                "success": True,
                "saved_stories": result["saved_stories"],
                "total_count": result["total_count"],
                "displayed_count": result["displayed_count"],
                "message": f"Found {result['total_count']} saved stories"
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error in get_saved_stories endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve saved stories")

@router.get("/check/{story_id}")
async def check_story_saved(
    story_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Check if a specific story is saved by the user"""
    
    try:
        is_saved = await SavedStoriesDatabase.is_story_saved(
            user_id=current_user["id"],
            story_id=story_id
        )
        
        return {
            "success": True,
            "story_id": story_id,
            "is_saved": is_saved
        }
        
    except Exception as e:
        logger.error(f"Error checking story save status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check story save status")

@router.get("/stats")
async def get_saved_stories_stats(
    current_user: dict = Depends(get_current_active_user)
):
    """Get statistics about user's saved stories"""
    
    try:
        stats = await SavedStoriesDatabase.get_saved_stories_stats(current_user["id"])
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting saved stories stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get saved stories statistics")

# Admin endpoint for cleanup
@router.post("/admin/cleanup")
async def cleanup_orphaned_saves(
    current_user: dict = Depends(get_current_active_user)
):
    """Clean up orphaned saved stories (admin only)"""
    
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        cleaned_count = await SavedStoriesDatabase.cleanup_orphaned_saves()
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} orphaned saved stories",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up orphaned saves: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup orphaned saves")