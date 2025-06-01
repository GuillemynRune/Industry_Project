from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
from datetime import datetime
from html import escape
import re

# Configuration and logging
from config import get_settings
from logging_config import setup_logging, add_request_id_middleware

# Routers
from routers import auth, stories, moderation, health
from routers.auth import get_current_active_user

# Services and database
from database.connection import connect_to_mongo, close_mongo_connection, mongodb
from database.models.story import StoryDatabase
from database.utils import CrisisSupport
from backup_manager import BackupManager

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize
settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Postnatal Stories API",
    description="API for transforming recovery stories and connecting parents",
    version="3.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Middleware
app.middleware("http")(add_request_id_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", 
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    })
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

# Models
class SearchRequest(BaseModel):
    query: str
    
    def sanitize_fields(self):
        self.query = sanitize_user_input(self.query)

# Include routers
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(moderation.router)
app.include_router(health.router)

# Backup router
backup_router = APIRouter(prefix="/admin/backup", tags=["admin"])
backup_manager = BackupManager(settings.mongodb_uri)

@backup_router.post("/create")
async def create_backup(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return await backup_manager.create_backup()

@backup_router.get("/list")
async def list_backups(current_user: dict = Depends(get_current_active_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"backups": backup_manager.list_backups()}

app.include_router(backup_router)

# Events
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    logger.info("Database connected successfully")
    
    required_vars = ["jwt_secret_key", "mongodb_uri"]
    missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise ValueError(f"Missing environment variables: {missing_vars}")
    
    logger.info(f"Starting Postnatal Stories API v3.0.0 in {settings.environment} mode")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    logger.info("Database connection closed")

# Routes
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

@app.get("/crisis-resources")
async def get_crisis_resources():
    """Get crisis support resources"""
    try:
        await CrisisSupport.log_crisis_interaction(interaction_type="crisis_resources_accessed")
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

@app.get("/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        return {"database_stats": await StoryDatabase.get_database_stats()}
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