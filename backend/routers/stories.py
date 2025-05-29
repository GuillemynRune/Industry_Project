from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from database.models.story import StoryDatabase
from database.models.symptom import SymptomDatabase
from database.models.moderation import ModerationDatabase
from database.utils import CrisisSupport, ContentFilter
from services.story_service import create_recovery_story_prompt
from services.symptom_service import extract_symptoms, get_symptom_insights
from services.ollama_client import query_ollama_model, MODELS
from routers.auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stories", tags=["stories"])

# Pydantic models
class StoryRequest(BaseModel):
    author_name: Optional[str] = "Anonymous"
    challenge: str
    experience: str
    solution: str
    advice: Optional[str] = ""

class StoryResponse(BaseModel):
    success: bool
    story: Optional[str] = None
    author_name: str
    message: str
    model_used: Optional[str] = None
    story_id: Optional[str] = None

# Helper functions
async def generate_recovery_story(challenge: str, experience: str, solution: str, advice: str = "", author_name: str = "Anonymous") -> dict:
    """Generate a recovery story using Ollama and save to database"""
    
    try:
        prompt = create_recovery_story_prompt(challenge, experience, solution, advice)
        
        story = None
        model_used = None
        
        for model_name in MODELS:
            try:
                logger.info(f"Trying model: {model_name}")
                
                generated_text = query_ollama_model(model_name, prompt, max_tokens=150)
                
                if generated_text and len(generated_text.strip()) > 100:
                    story = generated_text.strip()
                    model_used = model_name
                    break
                        
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}")
                continue
        
        if not story or len(story.strip()) < 100:
            story = create_fallback_recovery_story(challenge, experience, solution, advice)
            model_used = "fallback"
            logger.info("Used fallback recovery story")

        try:
            symptom_data = extract_symptoms(
                experience=f"{challenge}. {experience}",
                feelings=advice
            )
            key_symptoms = symptom_data.get("symptoms_identified", [])[:3]
            logger.info(f"Extracted key symptoms: {key_symptoms}")
        except Exception as e:
            logger.warning(f"Symptom extraction failed: {e}")
            key_symptoms = []
        
        return {
            "success": True,
            "story": story,
            "author_name": author_name,
            "model_used": model_used,
            "key_symptoms": key_symptoms,
            "message": f"Recovery story created using {model_used}"
        }
        
    except Exception as e:
        logger.error(f"Error generating recovery story: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "story": create_fallback_recovery_story(challenge, experience, solution, advice),
            "author_name": author_name,
            "model_used": "fallback",
            "key_symptoms": []
        }

def create_fallback_recovery_story(challenge: str, experience: str, solution: str, advice: str = "") -> str:
    """Create a recovery story when AI models fail"""
    story = f"Recovery Story: Overcoming {challenge}\n\n"
    story += f"The challenge: {experience[:150]}{'...' if len(experience) > 150 else ''}\n\n"
    story += f"What helped: {solution[:150]}{'...' if len(solution) > 150 else ''}\n\n"
    if advice:
        story += f"Advice to others: {advice[:100]}{'...' if len(advice) > 100 else ''}\n\n"
    story += "Remember: Recovery is possible. Every small step forward matters, and you're not alone in this journey."
    
    return story

# Routes
@router.post("/submit")
async def submit_story_for_review(
    request: Request,
    story_request: StoryRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Submit a story for moderation review (requires authentication)"""
    
    if not story_request.challenge.strip() or not story_request.experience.strip() or not story_request.solution.strip():
        raise HTTPException(status_code=400, detail="Challenge, experience, and solution cannot be empty")
    
    try:
        combined_text = f"{story_request.experience} {story_request.advice}"
        risk_assessment = ContentFilter.get_risk_assessment(combined_text)
        
        if risk_assessment["requires_intervention"]:
            await CrisisSupport.log_crisis_interaction(
                user_id=current_user["id"],
                interaction_type="crisis_content_detected"
            )
            
            crisis_resources = CrisisSupport.get_crisis_resources()
            return {
                "success": False,
                "requires_immediate_support": True,
                "crisis_resources": crisis_resources,
                "message": "We noticed your message indicates you might be in distress. Please reach out for immediate support."
            }
        
        story_result = await generate_recovery_story(
            challenge=story_request.challenge,
            experience=story_request.experience,
            solution=story_request.solution,
            advice=story_request.advice,
            author_name=story_request.author_name or current_user.get("display_name", "Anonymous")
        )
        
        if not story_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate story")
        
        moderation_result = await ModerationDatabase.submit_story_for_review(
            user_id=current_user["id"],
            author_name=story_request.author_name or current_user.get("display_name", "Anonymous"),
            challenge=story_request.challenge,
            experience=story_request.experience,
            solution=story_request.solution,
            advice=story_request.advice,
            generated_story=story_result["story"],
            model_used=story_result["model_used"],
            key_symptoms=story_result.get("key_symptoms", [])
        )
        
        return {
            "success": True,
            "message": "Your story has been submitted for review and will be published within 24-48 hours.",
            "story_id": moderation_result["story_id"],
            "estimated_review_time": moderation_result["estimated_review_time"],
            "story_preview": story_result["story"][:200] + "..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit story")

@router.get("/")
async def get_approved_stories(limit: int = 20, skip: int = 0, random: bool = True):
    """Get approved recovery stories only"""
    try:
        stories = await StoryDatabase.get_recovery_stories(limit=limit, skip=skip)
        
        if random and len(stories) > limit:
            import random as rand
            rand.shuffle(stories)
            stories = stories[:limit]
        
        for story in stories:
            if 'match_percentage' in story:
                del story['match_percentage']
            if 'similarity_score' in story:
                del story['similarity_score']
            story.pop("user_id", None)
            story.pop("moderated_by", None)
            story.pop("moderation_notes", None)
        
        return {
            "success": True,
            "stories": stories,
            "count": len(stories)
        }
    except Exception as e:
        logger.error(f"Error getting stories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stories: {str(e)}")

@router.get("/{story_id}")
async def get_story(story_id: str):
    """Get a specific story by ID"""
    try:
        story = await StoryDatabase.get_story_by_id(story_id)
        if story:
            if 'match_percentage' in story:
                del story['match_percentage']
            if 'similarity_score' in story:
                del story['similarity_score']
            
            return {"success": True, "story": story}
        else:
            raise HTTPException(status_code=404, detail="Story not found")
    except Exception as e:
        logger.error(f"Error getting story {story_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get story: {str(e)}")