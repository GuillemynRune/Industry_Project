from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from database.models.story import StoryDatabase
from database.models.moderation import ModerationDatabase
from database.utils import CrisisSupport, ContentFilter
from database.connection import mongodb
from services.story_service import create_recovery_story_prompt, find_similar_stories, get_story_recommendations, generate_recovery_story
from services.symptom_service import extract_symptoms
from services.openai_client import query_openai_model, MODELS
from routers.auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stories", tags=["stories"])

# Models
class StoryRequest(BaseModel):
    author_name: Optional[str] = "Anonymous"
    challenge: str
    experience: str
    solution: str
    advice: Optional[str] = ""

class SimilarityRequest(BaseModel):
    story: str

class RecommendationRequest(BaseModel):
    challenge: str
    experience: str

def create_fallback_recovery_story(challenge: str, experience: str, solution: str, advice: str = "") -> str:
    """Create fallback story when AI models fail"""
    story = f"Recovery Story: Overcoming {challenge}\n\n"
    story += f"The challenge: {experience[:150]}{'...' if len(experience) > 150 else ''}\n\n"
    story += f"What helped: {solution[:150]}{'...' if len(solution) > 150 else ''}\n\n"
    if advice:
        story += f"Advice to others: {advice[:100]}{'...' if len(advice) > 100 else ''}\n\n"
    story += "Remember: Recovery is possible. Every small step forward matters, and you're not alone in this journey."
    return story

# REMOVED the local generate_recovery_story function - using the one from story_service instead

@router.post("/submit")
async def submit_story_for_review(
    request: Request,
    story_request: StoryRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Submit story for moderation review"""
    
    # Validate required fields
    if not all([story_request.challenge.strip(), story_request.experience.strip(), story_request.solution.strip()]):
        raise HTTPException(status_code=400, detail="Challenge, experience, and solution cannot be empty")
    
    # Check for crisis content
    combined_text = f"{story_request.experience} {story_request.advice}"
    risk_assessment = ContentFilter.get_risk_assessment(combined_text)
    
    if risk_assessment["requires_intervention"]:
        await CrisisSupport.log_crisis_interaction(
            user_id=current_user["id"],
            interaction_type="crisis_content_detected"
        )
        
        return {
            "success": False,
            "requires_immediate_support": True,
            "crisis_resources": CrisisSupport.get_crisis_resources(),
            "message": "We noticed your message indicates you might be in distress. Please reach out for immediate support."
        }
    
    # DEBUG: Check what function we're actually calling
    logger.info("🔍 DEBUG: About to call generate_recovery_story function")
    logger.info(f"🔍 DEBUG: Function location: {generate_recovery_story}")
    
    # Generate story WITH embedding - now using the correct function from story_service!
    logger.info("Generating recovery story with embedding for submission")
    story_result = await generate_recovery_story(
        challenge=story_request.challenge,
        experience=story_request.experience,
        solution=story_request.solution,
        advice=story_request.advice,
        author_name=story_request.author_name or current_user.get("display_name", "Anonymous")
    )
    
    logger.info(f"🔍 DEBUG: Story result keys: {list(story_result.keys())}")
    logger.info(f"🔍 DEBUG: Story result success: {story_result.get('success')}")
    logger.info(f"🔍 DEBUG: Story result embedding present: {story_result.get('embedding') is not None}")
    
    if not story_result["success"]:
        raise HTTPException(status_code=500, detail="Failed to generate story")
    
    logger.info(f"Story generation result - embedding present: {story_result.get('embedding') is not None}")
    
    # Submit for moderation WITH the embedding
    moderation_result = await ModerationDatabase.submit_story_for_review(
        user_id=current_user["id"],
        author_name=story_request.author_name or current_user.get("display_name", "Anonymous"),
        challenge=story_request.challenge,
        experience=story_request.experience,
        solution=story_request.solution,
        advice=story_request.advice,
        generated_story=story_result["story"],
        model_used=story_result["model_used"],
        key_symptoms=story_result.get("key_symptoms", []),
        embedding=story_result.get("embedding")  # Pass the embedding here!
    )
    
    return {
        "success": True,
        "message": "Your story has been submitted for review and will be published within 24-48 hours.",
        "story_id": moderation_result["story_id"],
        "estimated_review_time": moderation_result["estimated_review_time"],
        "story_preview": story_result["story"][:200] + "...",
        "embedding_generated": story_result.get("embedding") is not None
    }

@router.get("/")
async def get_approved_stories(limit: int = 20, skip: int = 0, random: bool = True):
    """Get approved recovery stories"""
    stories = await StoryDatabase.get_recovery_stories(limit=limit, skip=skip)
    
    if random and len(stories) > limit:
        import random as rand
        rand.shuffle(stories)
        stories = stories[:limit]
    
    # Clean sensitive data
    for story in stories:
        story.pop("user_id", None)
        story.pop("moderated_by", None)
        story.pop("moderation_notes", None)
        story.pop("match_percentage", None)
        story.pop("similarity_score", None)
    
    return {
        "success": True,
        "stories": stories,
        "count": len(stories)
    }

@router.get("/{story_id}")
async def get_story(story_id: str):
    """Get specific story by ID"""
    story = await StoryDatabase.get_story_by_id(story_id)
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Clean sensitive data
    story.pop("match_percentage", None)
    story.pop("similarity_score", None)
    
    return {"success": True, "story": story}

@router.post("/find-similar")
async def find_similar_stories_endpoint(
    request: SimilarityRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Find stories similar to the user's input"""
    
    if not request.story.strip():
        raise HTTPException(status_code=400, detail="Story text is required")
    
    if len(request.story.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide more details about your situation")
    
    try:
        similar_stories = await find_similar_stories(
            input_story=request.story,
            top_k=9,
            min_similarity=0.1
        )
        
        return {
            "success": True,
            "stories": similar_stories,
            "total_found": len(similar_stories),
            "message": "Found similar stories" if similar_stories else "No similar stories found"
        }
        
    except Exception as e:
        logger.error(f"Error in find_similar_stories_endpoint: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while finding similar stories")

@router.post("/recommendations")
async def get_story_recommendations_endpoint(
    request: RecommendationRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Get story recommendations based on user's challenge and experience"""
    
    if not request.challenge.strip() or not request.experience.strip():
        raise HTTPException(status_code=400, detail="Challenge and experience are required")
    
    try:
        recommendations = await get_story_recommendations(
            user_challenge=request.challenge,
            user_experience=request.experience
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error in get_story_recommendations_endpoint: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while getting story recommendations")

@router.get("/themes/analysis")
async def get_story_themes_analysis(current_user: dict = Depends(get_current_active_user)):
    """Get analysis of common themes in stories"""
    try:
        return {
            "success": True,
            "message": "Theme analysis endpoint - implement based on your needs",
            "common_themes": [
                "depression", "anxiety", "isolation", "sleep", 
                "feeding", "bonding", "identity", "support"
            ]
        }
    except Exception as e:
        logger.error(f"Error in themes analysis: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while analyzing themes")
    
@router.get("/user/stories")
async def get_user_stories(
    current_user: dict = Depends(get_current_active_user),
    limit: int = 20,
    skip: int = 0
):
    """Get current user's submitted stories"""
    try:
        # Get from pending, approved, and rejected collections
        pending_stories = []
        approved_stories = []
        rejected_stories = []
        
        # Pending stories
        pending_cursor = mongodb.database.pending_stories.find(
            {"user_id": current_user["id"]}
        ).sort("created_at", -1).limit(limit)
        
        async for story in pending_cursor:
            story["id"] = str(story["_id"])
            story["status"] = "pending"
            del story["_id"]
            pending_stories.append(story)
        
        # Approved stories
        approved_cursor = mongodb.database.approved_stories.find(
            {"user_id": current_user["id"]}
        ).sort("created_at", -1).limit(limit)
        
        async for story in approved_cursor:
            story["id"] = str(story["_id"])
            story["status"] = "approved"
            del story["_id"]
            approved_stories.append(story)
        
        # Rejected stories
        rejected_cursor = mongodb.database.rejected_stories.find(
            {"user_id": current_user["id"]}
        ).sort("created_at", -1).limit(limit)
        
        async for story in rejected_cursor:
            story["id"] = str(story["_id"])
            story["status"] = "rejected"
            del story["_id"]
            rejected_stories.append(story)
        
        # Combine and sort by date
        all_stories = pending_stories + approved_stories + rejected_stories
        all_stories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "success": True,
            "stories": all_stories[:limit],
            "total_count": len(all_stories),
            "pending_count": len(pending_stories),
            "approved_count": len(approved_stories),
            "rejected_count": len(rejected_stories)
        }
        
    except Exception as e:
        logger.error(f"Error fetching user stories: {e}")
        raise HTTPException(status_code=500, detail="Error fetching stories")