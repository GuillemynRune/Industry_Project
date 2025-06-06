"""
Story transformation service using Ollama models
"""

import logging
from .openai_client import query_openai_model, MODELS

logger = logging.getLogger(__name__)

def create_recovery_story_prompt(challenge: str, experience: str, solution: str, advice: str = "") -> str:
    """Create a recovery story from user's input"""
    return f"""Write a concise, inspiring recovery story (~150 words NOT MORE) based on this person's experience:

Challenge: {challenge}
Experience: {experience}  
Solution: {solution}
Advice: {advice}

Create a short, compelling narrative that:
- Tells their story in a warm, relatable way
- Highlights the key turning points
- Includes specific, actionable solutions
- Ends with hope and encouragement
- Keeps it concise but emotionally resonant

Write in third person, make it feel authentic, and focus on the most important parts of their journey. Keep it UNDER 200 words.

Story:"""

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
    """Generate supportive message from user's experience using Ollama"""
    
    prompt = create_supportive_message_prompt(experience, feelings)
    
    # Try models in order
    for model_name in MODELS:
        try:
            generated_text = query_openai_model(model_name, prompt, max_tokens=300)
            
            if generated_text and len(generated_text.strip()) > 50:
                return {
                    "success": True,
                    "story": generated_text.strip(),
                    "author_name": author_name,
                    "model_used": model_name,
                    "message": f"Supportive message created using {model_name}"
                }
                        
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {str(e)}")
            continue
    
    # Fallback if all models fail
    story = create_fallback_supportive_message(experience, feelings)
    return {
        "success": True,
        "story": story,
        "author_name": author_name,
        "model_used": "fallback",
        "message": "Supportive message created using fallback"
    }

def create_fallback_supportive_message(experience: str, feelings: str) -> str:
    """Create supportive message when AI models fail"""
    message = f"What you're experiencing is completely valid and more common than you might think. "
    message += f"The challenges you're facing - {experience[:80]}{'...' if len(experience) > 80 else ''} - are part of the intense reality of early parenthood that many don't talk openly about. "
    message += f"Your feelings of {feelings[:60]}{'...' if len(feelings) > 60 else ''} make perfect sense given what you're going through. "
    message += f"You're not alone in this, and you're doing better than you think. These difficult moments don't define your worth as a parent. "
    message += f"Be gentle with yourself - you're navigating one of life's biggest transitions, and it's okay to struggle while you find your way."
    
    return message