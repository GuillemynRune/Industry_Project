from fastapi import APIRouter
from database.connection import check_database_health
import psutil
from datetime import datetime

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    """Main health check endpoint"""
    db_healthy = await check_database_health()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database_connected": db_healthy,
        "features_enabled": [
            "recovery_story_generation", 
            "symptom_extraction", 
            "database_storage", 
            "authentication", 
            "moderation"
        ]
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed system health check"""
    db_healthy = await check_database_health()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "checks": {
            "database": db_healthy,
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "cpu_percent": psutil.cpu_percent()
            }
        }
    }