from fastapi import APIRouter
from services.ollama_client import validate_ollama_connection, test_model_connection, MODELS
from database.connection import check_database_health
import psutil
from datetime import datetime

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    """Main health check endpoint"""
    ollama_connected, ollama_info = validate_ollama_connection()
    db_healthy = await check_database_health()
    
    return {
        "status": "healthy" if (ollama_connected and db_healthy) else "degraded",
        "ollama_connected": ollama_connected,
        "ollama_info": ollama_info,
        "database_connected": db_healthy,
        "available_models": len(MODELS),
        "features_enabled": ["recovery_story_generation", "symptom_extraction", "database_storage", "authentication", "moderation"]
    }

@router.get("/health/detailed")
async def detailed_health_check():
    checks = {
        "database": await check_database_health(),
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "cpu_percent": psutil.cpu_percent()
        }
    }
    
    status = "healthy" if checks["database"] else "unhealthy"
    return {"status": status, "checks": checks}

@router.get("/models/test")
async def test_models():
    """Test Ollama connection and models"""
    
    ollama_connected, ollama_info = validate_ollama_connection()
    
    test_results = []
    if ollama_connected:
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