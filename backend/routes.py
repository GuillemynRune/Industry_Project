from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from pydantic import BaseModel
import logging
from datetime import datetime
from html import escape
import re

from routers import auth, stories, moderation, health
from routers.auth import get_current_active_user
from database.connection import mongodb
from database.models.story import StoryDatabase
from database.utils import CrisisSupport
from backup_manager import BackupManager
from slowapi import Limiter
from slowapi.util import get_remote_address
from routers import tts

logger = logging.getLogger(__name__)

def sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    return escape(text).strip()

class SearchRequest(BaseModel):
    query: str
    
    def sanitize_fields(self):
        self.query = sanitize_user_input(self.query)

def setup_routes(app: FastAPI, settings):
    """Configure all application routes"""
    
    # Include existing routers
    app.include_router(auth.router)
    app.include_router(stories.router)
    app.include_router(moderation.router)
    app.include_router(health.router)
    app.include_router(tts.router)
    
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
    
    # Rate limiter for custom routes
    limiter = Limiter(key_func=get_remote_address)
    
    # Main routes
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