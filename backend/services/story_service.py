"""
Story transformation service using Ollama models
"""

import logging
import traceback
from .openai_client import query_openai_model, MODELS
from database.connection import mongodb
from typing import List, Dict
from .story_matcher import story_matcher

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

async def find_similar_stories(input_story: str, top_k: int = 9, min_similarity: float = 0.1) -> List[Dict]:
    """Find similar stories using semantic similarity"""
    try:
        stories_collection = mongodb.database.approved_stories
        
        return await story_matcher.find_similar_stories_with_embeddings(
            input_text=input_story,
            stories_collection=stories_collection,
            top_k=top_k,
            min_similarity=min_similarity
        )
    except Exception as e:
        logger.error(f"Error finding similar stories: {e}")
        return []
    
def create_story_with_embedding(story_data: dict) -> dict:
    """Create story and generate embedding with detailed debugging"""
    try:
        logger.info("Starting embedding generation process")
        logger.info(f"Story data keys: {list(story_data.keys())}")
        
        # Check if story_matcher is available
        if not hasattr(story_matcher, 'model') or story_matcher.model is None:
            logger.error("Story matcher model not available")
            return story_data
        
        # Create the text for embedding
        story_text = story_matcher.create_story_embedding_text(story_data)
        
        if not story_text or story_text == "Error creating embedding text":
            logger.error("Failed to create story text for embedding")
            return story_data
        
        logger.info(f"Created story text for embedding: length={len(story_text)}")
        
        # Generate the embedding
        embedding = story_matcher.generate_embedding(story_text)
        
        if embedding and len(embedding) > 0:
            story_data["embedding"] = embedding
            logger.info(f"✓ Successfully generated embedding with length: {len(embedding)}")
            logger.info(f"Embedding sample: {embedding[:5]}...")  # Show first 5 values
        else:
            logger.warning("Failed to generate embedding - embedding is empty or None")
            story_data["embedding"] = None
        
        return story_data
        
    except Exception as e:
        logger.error(f"Error creating story with embedding: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return story_data

async def generate_recovery_story(
    challenge: str, 
    experience: str, 
    solution: str, 
    advice: str = "", 
    author_name: str = "Anonymous"
) -> dict:
    """Generate recovery story with AI models and fallback - with embedding debugging"""
    
    logger.info("Starting recovery story generation")
    
    prompt = create_recovery_story_prompt(challenge, experience, solution, advice)
    story = None
    model_used = None
    
    # Try AI models
    for model_name in MODELS:
        try:
            generated_text = query_openai_model(model_name, prompt, max_tokens=300)
            if generated_text and len(generated_text.strip()) > 100:
                story = generated_text.strip()
                model_used = model_name
                logger.info(f"✓ Story generated using {model_name}")
                break
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {str(e)}")
            continue
    
    # Fallback
    if not story or len(story.strip()) < 100:
        story = create_fallback_recovery_story(challenge, experience, solution, advice)
        model_used = "fallback"
        logger.info("Using fallback story generation")
    
    # Extract symptoms
    key_symptoms = []
    try:
        from .symptom_service import extract_symptoms
        symptom_data = extract_symptoms(f"{challenge}. {experience}", advice)
        key_symptoms = symptom_data.get("symptoms_identified", [])[:3]
        logger.info(f"Extracted symptoms: {key_symptoms}")
    except Exception as e:
        logger.warning(f"Symptom extraction failed: {e}")
    
    # Create story data
    story_data = {
        "challenge": challenge,
        "experience": experience,
        "solution": solution,
        "advice": advice,
        "generated_story": story,
        "author_name": author_name,
        "model_used": model_used,
        "key_symptoms": key_symptoms
    }
    
    logger.info("Creating story with embedding...")
    story_data_with_embedding = create_story_with_embedding(story_data)
    
    # Log embedding status
    if story_data_with_embedding.get("embedding"):
        logger.info("✓ Embedding successfully added to story")
    else:
        logger.warning("❌ No embedding was added to story")
    
    return {
        "success": True,
        "story": story,
        "author_name": author_name,
        "model_used": model_used,
        "key_symptoms": key_symptoms,
        "embedding": story_data_with_embedding.get("embedding"),
        "message": f"Recovery story created using {model_used}"
    }

def create_fallback_recovery_story(challenge: str, experience: str, solution: str, advice: str = "") -> str:
    """Create fallback story when AI models fail"""
    story = f"Recovery Story: Overcoming {challenge}\n\n"
    story += f"The challenge: {experience[:150]}{'...' if len(experience) > 150 else ''}\n\n"
    story += f"What helped: {solution[:150]}{'...' if len(solution) > 150 else ''}\n\n"
    if advice:
        story += f"Advice to others: {advice[:100]}{'...' if len(advice) > 100 else ''}\n\n"
    story += "Remember: Recovery is possible. Every small step forward matters, and you're not alone in this journey."
    return story

async def get_story_recommendations(user_challenge: str, user_experience: str) -> Dict:
    """Get story recommendations based on user input"""
    combined_input = f"{user_challenge}. {user_experience}"
    
    try:
        similar_stories = await find_similar_stories(combined_input, top_k=9, min_similarity=0.1)
        
        if similar_stories:
            return {
                "success": True,
                "message": "Found stories from others with similar experiences",
                "stories": similar_stories,
                "total_found": len(similar_stories)
            }
        else:
            return {
                "success": True,
                "message": "No similar stories found, but you're not alone in your journey",
                "stories": [],
                "total_found": 0
            }
    except Exception as e:
        logger.error(f"Error getting story recommendations: {e}")
        return {
            "success": False,
            "message": "Unable to find similar stories at this time",
            "stories": [],
            "total_found": 0
        }