"""
Story transformation service
Handles converting user experiences into supportive messages using Ollama
"""

import logging
from typing import Optional, List
from .ollama_client import query_ollama_model, OLLAMA_MODEL, MODELS

logger = logging.getLogger(__name__)

def create_recovery_story_prompt(challenge: str, experience: str, solution: str, advice: str = "") -> str:
    """Create a recovery story from user's input"""
    return f"""You are a story editor helping transform recovery experiences into inspiring, helpful stories for other parents.

Transform this recovery story into a well-structured, inspiring narrative that will help others facing similar challenges.

Challenge faced: {challenge}
Personal experience: {experience}
What helped/solution: {solution}
Advice to others: {advice}

Create a cohesive story (100-150 words) that:
- Starts with acknowledging the challenge
- Describes the experience authentically
- Explains what helped and how recovery happened
- Ends with hope and practical advice
- Uses a warm, encouraging tone
- Could genuinely help someone in a similar situation

Write the story in third person or first person, whichever flows better."""

def create_supportive_message_prompt(experience: str, feelings: str) -> str:
    """Create a supportive, encouraging response prompt"""
    return f"""You are a compassionate peer support specialist helping parents. Take their experience and transform it into a supportive, validating message.

Your response should:
- Acknowledge and validate their feelings
- Normalize their experience 
- Offer gentle perspective and encouragement
- Be warm, understanding, and non-judgmental
- Be 150-250 words
- Focus on hope and reassurance while honoring their struggle

Experience: {experience}

Feelings: {feelings}

Write a compassionate response that acknowledges their struggle, normalizes their experience, and offers gentle encouragement."""

def generate_supportive_message(experience: str, feelings: str, author_name: str = "Anonymous") -> dict:
    """Generate a supportive message from user's experience using Ollama"""
    
    try:
        prompt = create_supportive_message_prompt(experience, feelings)
        
        # Try models in order of preference
        story = None
        model_used = None
        
        for model_name in MODELS:
            try:
                logger.info(f"Trying model: {model_name}")
                
                generated_text = query_ollama_model(model_name, prompt, max_tokens=300)
                
                if generated_text and len(generated_text.strip()) > 50:
                    story = generated_text.strip()
                    model_used = model_name
                    break
                        
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}")
                continue
        
        # Fallback response if no model worked
        if not story or len(story.strip()) < 50:
            story = create_fallback_supportive_message(experience, feelings)
            model_used = "fallback"
            logger.info("Used fallback supportive response")
        
        return {
            "success": True,
            "story": story,
            "author_name": author_name,
            "model_used": model_used,
            "message": f"Supportive message created using {model_used}"
        }
        
    except Exception as e:
        logger.error(f"Error generating supportive message: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "story": create_fallback_supportive_message(experience, feelings),
            "author_name": author_name,
            "model_used": "fallback"
        }

def create_fallback_supportive_message(experience: str, feelings: str) -> str:
    """Create a supportive message when AI models fail"""
    message = f"What you're experiencing is completely valid and more common than you might think. "
    message += f"The challenges you're facing - {experience[:80]}{'...' if len(experience) > 80 else ''} - are part of the intense reality of early parenthood that many don't talk openly about. "
    message += f"Your feelings of {feelings[:60]}{'...' if len(feelings) > 60 else ''} make perfect sense given what you're going through. "
    message += f"You're not alone in this, and you're doing better than you think. These difficult moments don't define your worth as a parent. "
    message += f"Be gentle with yourself - you're navigating one of life's biggest transitions, and it's okay to struggle while you find your way."
    
    return message