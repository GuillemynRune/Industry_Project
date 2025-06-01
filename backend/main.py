# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List
import uvicorn
import logging
import os
from datetime import datetime

# Import configuration and logging
from config import get_settings
from logging_config import setup_logging, add_request_id_middleware

# Import routers
from routers import auth, stories, moderation, health
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.story_service import create_recovery_story_prompt
from services.symptom_service import extract_symptoms, get_symptom_insights
from services.ollama_client import validate_ollama_connection, test_model_connection, MODELS, query_ollama_model

from database import connect_to_mongo, close_mongo_connection, CrisisSupport, mongodb
from database.models.story import StoryDatabase

from services.ollama_client import query_ollama_model, MODELS

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from html import escape
import re

# Get settings
settings = get_settings()

# Setup logging
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Postnatal Stories API",
    description="API for transforming recovery stories and connecting parents",
    version="3.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add request ID middleware for tracing
app.middleware("http")(add_request_id_middleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    return escape(text).strip()

# Include routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(moderation.router)
app.include_router(health.router)

# Add backup router
from backup_manager import BackupManager
from fastapi import APIRouter, Depends
from routers.auth import get_current_active_user

backup_router = APIRouter(prefix="/admin/backup", tags=["admin"])
backup_manager = BackupManager(settings.mongodb_uri)

@backup_router.post("/create")
async def create_backup(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    result = await backup_manager.create_backup()
    return result

@backup_router.get("/list")
async def list_backups(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"backups": backup_manager.list_backups()}

app.include_router(backup_router)

class SearchRequest(BaseModel):
    query: str
    
    def sanitize_fields(self):
        self.query = sanitize_user_input(self.query)

# Database events
@app.on_event("startup")
async def startup_event():
    try:
        await connect_to_mongo()
        logger.info("Database connected successfully on startup")
        
        required_vars = ["JWT_SECRET_KEY", "MONGODB_URI"]
        missing_vars = [var for var in required_vars if not getattr(settings, var.lower(), None)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            raise ValueError(f"Missing environment variables: {missing_vars}")
        
        logger.info(f"Starting Postnatal Stories API v3.0.0 in {settings.environment} mode")
        
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
        "message": "Postnatal Recovery Stories API v3.0 - Production Ready!",
        "environment": settings.environment,
        "features": [
            "Recovery story transformation",
            "Symptom extraction", 
            "Support insights",
            "User authentication",
            "Content moderation",
            "Crisis support",
            "MongoDB database storage",
            "Structured logging",
            "Automated backups"
        ],
        "security": "Enhanced security enabled",
        "documentation": "/docs" if settings.debug else "Contact admin for API documentation"
    }

# Search endpoint
@app.post("/search-similar")
@limiter.limit("20/minute")
async def search_similar_stories(request: Request, search_request: SearchRequest):
    """Search for similar recovery stories"""
    
    search_request.sanitize_fields()
    
    try:
        stories = await StoryDatabase.search_recovery_stories(search_request.query, limit=10)
        
        return {
            "success": True,
            "message": f"Found {len(stories)} stories",
            "results": stories
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "success": False,
            "message": f"Search failed: {str(e)}",
            "results": []
        }

# Crisis resources
@app.get("/crisis-resources")
async def get_crisis_resources():
    """Get crisis support resources"""
    try:
        await CrisisSupport.log_crisis_interaction(
            interaction_type="crisis_resources_accessed"
        )
        
        return {
            "success": True,
            "resources": CrisisSupport.get_crisis_resources(),
            "message": "If you're in immediate danger, call emergency services (911)"
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
        
        return {
            "database_stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    try:
        stats = await StoryDatabase.get_database_stats()
        pending_stories = await mongodb.database.pending_stories.count_documents({"status": "pending_review"})
        total_users = await mongodb.database.users.count_documents({})
        
        return {
            "total_stories": stats.get("total_stories", 0),
            "pending_stories": pending_stories,
            "total_users": total_users,
            "database_connected": stats.get("database_connected", False),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            "error": "Metrics unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )