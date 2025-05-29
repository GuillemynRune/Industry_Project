from fastapi import APIRouter
from services.ollama_client import validate_ollama_connection, MODELS


router = APIRouter(prefix="/health")


@router.get("/health")
async def health_check():
    from backend.database.database import check_database_health

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