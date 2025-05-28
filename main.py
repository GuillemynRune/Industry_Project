# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict, List
import logging

# Import our modular services (updated for Ollama)
from services.story_service import create_recovery_story_prompt
from services.symptom_service import extract_symptoms, get_symptom_insights
from services.ollama_client import validate_ollama_connection, test_model_connection, MODELS, query_ollama_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Postnatal Stories API",
    description="API for transforming recovery stories and connecting parents (using Ollama)",
    version="2.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class StoryRequest(BaseModel):
    author_name: Optional[str] = "Anonymous"
    challenge: str  # What challenge they faced
    experience: str  # Their experience with it
    solution: str   # What helped them recover
    advice: Optional[str] = ""  # Advice to others

class StoryResponse(BaseModel):
    success: bool
    story: Optional[str] = None
    author_name: str
    message: str
    model_used: Optional[str] = None

class SymptomRequest(BaseModel):
    experience: str
    feelings: str

class SymptomResponse(BaseModel):
    success: bool
    symptoms_identified: List[str]
    severity_indicators: List[str]
    categories_affected: List[str]
    key_concerns: List[str]
    extraction_method: str
    insights: Dict
    message: str

class SearchRequest(BaseModel):
    query: str

def generate_recovery_story(challenge: str, experience: str, solution: str, advice: str = "", author_name: str = "Anonymous") -> dict:
    """Generate a recovery story using Ollama"""
    
    try:
        prompt = create_recovery_story_prompt(challenge, experience, solution, advice)
        
        # Try models in order of preference
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
        
        # Fallback response if no model worked
        if not story or len(story.strip()) < 100:
            story = create_fallback_recovery_story(challenge, experience, solution, advice)
            model_used = "fallback"
            logger.info("Used fallback recovery story")
        
        return {
            "success": True,
            "story": story,
            "author_name": author_name,
            "model_used": model_used,
            "message": f"Recovery story created using {model_used}"
        }
        
    except Exception as e:
        logger.error(f"Error generating recovery story: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "story": create_fallback_recovery_story(challenge, experience, solution, advice),
            "author_name": author_name,
            "model_used": "fallback"
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

@app.get("/")
async def root():
    return {
        "message": "Postnatal Recovery Stories API v2.1 - Using Ollama!",
        "features": [
            "Recovery story transformation (local AI)",
            "Symptom extraction (local AI)", 
            "Support insights",
            "Story search (coming soon)"
        ],
        "ollama_required": "Make sure Ollama is running with phi4 model"
    }

@app.get("/health")
async def health_check():
    ollama_connected, ollama_info = validate_ollama_connection()
    return {
        "status": "healthy" if ollama_connected else "degraded",
        "ollama_connected": ollama_connected,
        "ollama_info": ollama_info,
        "available_models": len(MODELS),
        "features_enabled": ["recovery_story_generation", "symptom_extraction"]
    }

@app.post("/transform-story", response_model=StoryResponse)
async def transform_recovery_story(request: StoryRequest):
    """Transform recovery experience into inspiring story using Ollama"""
    
    if not request.challenge.strip() or not request.experience.strip() or not request.solution.strip():
        raise HTTPException(status_code=400, detail="Challenge, experience, and solution cannot be empty")
    
    try:
        result = generate_recovery_story(
            challenge=request.challenge,
            experience=request.experience,
            solution=request.solution,
            advice=request.advice,
            author_name=request.author_name
        )
        
        return StoryResponse(
            success=result["success"],
            story=result["story"],
            author_name=result["author_name"],
            message=result["message"],
            model_used=result["model_used"]
        )
            
    except Exception as e:
        logger.error(f"Story transformation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create recovery story: {str(e)}")

@app.post("/extract-symptoms", response_model=SymptomResponse)
async def extract_postnatal_symptoms(request: SymptomRequest):
    """Extract symptoms using Ollama"""
    
    if not request.experience.strip():
        raise HTTPException(status_code=400, detail="Experience cannot be empty")
    
    try:
        # Extract symptoms
        symptom_data = extract_symptoms(
            experience=request.experience,
            feelings=request.feelings
        )
        
        # Generate insights
        insights = get_symptom_insights(symptom_data)
        
        return SymptomResponse(
            success=True,
            symptoms_identified=symptom_data.get("symptoms_identified", []),
            severity_indicators=symptom_data.get("severity_indicators", ["mild"]),
            categories_affected=symptom_data.get("categories_affected", []),
            key_concerns=symptom_data.get("key_concerns", []),
            extraction_method=symptom_data.get("extraction_method", "unknown"),
            insights=insights,
            message=f"Extracted {len(symptom_data.get('symptoms_identified', []))} symptoms using {symptom_data.get('extraction_method', 'unknown')} method"
        )
        
    except Exception as e:
        logger.error(f"Symptom extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract symptoms: {str(e)}")

@app.post("/search-similar")
async def search_similar_stories(request: SearchRequest):
    """Search for similar recovery stories (placeholder)"""
    return {
        "success": True,
        "message": f"Searching for recovery stories similar to: '{request.query}'",
        "results": []
    }

@app.get("/models/test")
async def test_models():
    """Test Ollama connection and models"""
    
    # Validate Ollama connection
    ollama_connected, ollama_info = validate_ollama_connection()
    
    test_results = []
    if ollama_connected:
        # Test first 2 models
        for model_name in MODELS[:2]:
            result = test_model_connection(model_name)
            test_results.append(result)
    
    return {
        "success": ollama_connected and any(r["success"] for r in test_results),
        "ollama_connected": ollama_connected,
        "ollama_info": ollama_info,
        "available_models": MODELS,
        "test_results": test_results,
        "instructions": "Run 'ollama pull phi4' to install the main model"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )