from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
import uvicorn
import logging

from config import get_settings
from logging_config import setup_logging
from middleware import setup_middleware
from routes import setup_routes
from database.connection import connect_to_mongo, close_mongo_connection

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

# Setup middleware and routes
setup_middleware(app, settings)
setup_routes(app, settings)

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )