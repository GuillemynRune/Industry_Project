# Fixed middleware.py with proper CORS handling
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from logging_config import add_request_id_middleware
import logging

logger = logging.getLogger(__name__)

def setup_middleware(app: FastAPI, settings):
    """Configure all application middleware with proper CORS"""
    
    # Request ID middleware
    app.middleware("http")(add_request_id_middleware)
    
    # CORS middleware - MUST be added early and configured properly
    origins = []
    if hasattr(settings, 'allowed_origins'):
        if isinstance(settings.allowed_origins, str):
            # Split comma-separated string
            origins = [origin.strip() for origin in settings.allowed_origins.split(',')]
        elif isinstance(settings.allowed_origins, list):
            origins = settings.allowed_origins
    
    # Default origins if none specified
    if not origins:
        origins = [
            "http://localhost:8080",
            "http://localhost:3000", 
            "http://localhost:5500",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5500"
        ]
    
    logger.info(f"CORS allowed origins: {origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,  # Important for auth
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
        allow_headers=[
            "Authorization", 
            "Content-Type", 
            "X-Request-ID",
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Mx-ReqToken",
            "Keep-Alive",
            "X-Requested-With"
        ],
        expose_headers=["X-Request-ID"],  # Headers that frontend can access
        max_age=600,  # Cache preflight responses for 10 minutes
    )
    
    # Custom CORS debug middleware
    @app.middleware("http")
    async def cors_debug_middleware(request: Request, call_next):
        # Log CORS-related info for debugging
        origin = request.headers.get("origin")
        method = request.method
        
        if origin:
            logger.debug(f"CORS request: {method} from origin: {origin}")
        
        response = await call_next(request)
        
        # Add additional CORS headers if needed
        if origin and method == "OPTIONS":
            logger.debug(f"Handling preflight request from {origin}")
            # These are handled by CORSMiddleware, but we can log them
        
        return response
    
    # Security headers middleware (after CORS)
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Only add security headers for non-OPTIONS requests
        if request.method != "OPTIONS":
            response.headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY", 
                "X-XSS-Protection": "1; mode=block",
                # Remove HSTS for development to avoid issues
                # "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            })
        
        return response
    
    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Alternative configuration for development
def setup_development_middleware(app: FastAPI):
    """More permissive CORS for development"""
    
    logger.info("Setting up development CORS middleware")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=False,  # Must be False when using wildcard
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    @app.middleware("http")
    async def development_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Add debug headers
        response.headers["X-Debug-Mode"] = "true"
        response.headers["X-CORS-Debug"] = "development"
        
        return response