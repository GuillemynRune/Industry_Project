# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import logging

# Import routers
from routers import auth, stories, moderation, health
import sys
import os

# 👇 Adds the root directory (where /backend lives) to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Import our modular services
from services.story_service import create_recovery_story_prompt
from services.symptom_service import extract_symptoms, get_symptom_insights
from services.ollama_client import validate_ollama_connection, test_model_connection, MODELS, query_ollama_model

# Import database functionality
from database import connect_to_mongo, close_mongo_connection, StoryDatabase, SymptomDatabase, CrisisSupport

# Import services
from services.symptom_service import extract_symptoms, get_symptom_insights
from services.ollama_client import query_ollama_model, MODELS

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(moderation.router)
app.include_router(health.router)

# Pydantic models for remaining endpoints
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
    insights: dict
    message: str

class SearchRequest(BaseModel):
    query: str

# Database connection events
@app.on_event("startup")
async def startup_event():
    try:
        await connect_to_mongo()
        logger.info("Database connected successfully on startup")
    except Exception as e:
        logger.error(f"Failed to connect to database on startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await close_mongo_connection()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Postnatal Recovery Stories API v2.1 - Using Ollama!",
        "features": [
            "Recovery story transformation (local AI)",
            "Symptom extraction (local AI)", 
            "Support insights",
            "User authentication",
            "Content moderation",
            "Crisis support",
            "MongoDB database storage"
        ],
        "ollama_required": "Make sure Ollama is running with phi4 model"
    }

# Symptom extraction endpoint
@app.post("/extract-symptoms", response_model=SymptomResponse)
async def extract_postnatal_symptoms(request: SymptomRequest):
    """Extract symptoms using Ollama and save to database"""
    
    if not request.experience.strip():
        raise HTTPException(status_code=400, detail="Experience cannot be empty")
    
    try:
        symptom_data = extract_symptoms(
            experience=request.experience,
            feelings=request.feelings
        )
        
        insights = get_symptom_insights(symptom_data)
        
        try:
            save_result = await SymptomDatabase.save_symptom_extraction(
                experience=request.experience,
                feelings=request.feelings,
                symptoms_identified=symptom_data.get("symptoms_identified", []),
                severity_indicators=symptom_data.get("severity_indicators", []),
                categories_affected=symptom_data.get("categories_affected", []),
                key_concerns=symptom_data.get("key_concerns", []),
                extraction_method=symptom_data.get("extraction_method", "unknown"),
                insights=insights
            )
            
            if save_result["success"]:
                logger.info(f"Symptom extraction saved with ID: {save_result['extraction_id']}")
            else:
                logger.error(f"Failed to save symptom extraction: {save_result['message']}")
                
        except Exception as db_error:
            logger.error(f"Database save error for symptom extraction: {str(db_error)}")
        
        return SymptomResponse(
            success=True,
            symptoms_identified=symptom_data.get("symptoms_identified", []),
            severity_indicators=symptom_data.get("severity_indicators", ["mild"]),
            categories_affected=symptom_data.get("categories_affected", []),
            key_concerns=symptom_data.get("key_concerns", []),
            extraction_method=symptom_data.get("extraction_method", "unknown"),
            insights=insights,
            message=f"Extracted {len(symptom_data.get('symptoms_identified', []))} symptoms using {symptom_data.get('extraction_method', 'unknown')} method and saved to database"
        )
        
    except Exception as e:
        logger.error(f"Symptom extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract symptoms: {str(e)}")

# Search endpoint
@app.post("/search-similar")
async def search_similar_stories(request: SearchRequest):
    """Search for similar recovery stories"""
    try:
        stories = await StoryDatabase.search_recovery_stories(request.query, limit=10)
        
        return {
            "success": True,
            "message": f"Found {len(stories)} recovery stories similar to: '{request.query}'",
            "results": stories
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "success": False,
            "message": f"Error searching for stories: {str(e)}",
            "results": []
        }

# Crisis resources endpoint
@app.get("/crisis-resources")
async def get_crisis_resources():
    """Get crisis support resources (public endpoint)"""
    try:
        await CrisisSupport.log_crisis_interaction(
            interaction_type="crisis_resources_accessed"
        )
        
        return {
            "success": True,
            "resources": CrisisSupport.get_crisis_resources(),
            "message": "If you're in immediate danger, please call emergency services (911) or go to your nearest emergency room."
        }
        
    except Exception as e:
        logger.error(f"Error getting crisis resources: {e}")
        return {
            "success": True,
            "resources": CrisisSupport.get_crisis_resources()
        }

# Stats endpoint
@app.get("/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        stats = await StoryDatabase.get_database_stats()
        symptom_patterns = await SymptomDatabase.get_symptom_patterns()
        
        return {
            "database_stats": stats,
            "symptom_patterns": symptom_patterns
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )