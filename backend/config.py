# config.py - Environment configuration
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Database - using your existing MongoDB URI
    mongodb_uri: str
    database_name: str = "postnatal_stories"
    
    # Authentication - using your existing JWT secret
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    password_reset_expire_minutes: int = 60  # 1 hour for password reset
    
    # CORS - using your existing origins
    allowed_origins: str = "http://localhost:3000"
    
    # Email Configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_from_name: str = "Postnatal Stories"
    
    # Azure OpenAI (optional - add when ready)
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_model: str = "gpt-4"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Story Matching Settings
    story_matcher_model: str = "all-distilroberta-v1"
    models_cache_dir: str = "./ai_models"
    similarity_threshold: float = 0.1
    max_similar_stories: int = 9
    
    @field_validator('allowed_origins')
    @classmethod
    def parse_origins(cls, v):
        return [origin.strip() for origin in v.split(',')]
    
    @field_validator('jwt_secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class DevelopmentSettings(Settings):
    debug: bool = True
    log_level: str = "DEBUG"

class ProductionSettings(Settings):
    debug: bool = False
    log_level: str = "WARNING"

def get_settings() -> Settings:
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()

# Use this in main.py
app_settings = get_settings()