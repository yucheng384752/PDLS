"""Main FastAPI application for PDLS backend"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

from src.core.config import settings
from src.api.auth import router as auth_router
from src.api.users import router as users_router
from src.api.v1 import v1_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format=settings.LOG_FORMAT
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("PDLS Backend starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    yield
    
    # Shutdown
    logger.info("PDLS Backend shutting down...")


def create_app() -> FastAPI:
    """Create FastAPI application instance"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Project Development Log System API",
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Add trusted host middleware in production
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
        )
    
    # Include routers
    app.include_router(
        auth_router,
        prefix=settings.API_V1_PREFIX
    )
    app.include_router(
        users_router,
        prefix=settings.API_V1_PREFIX
    )
    app.include_router(
        v1_router,
        prefix="/api"
    )
    app.include_router(
        v1_router,
        prefix=settings.API_V1_PREFIX
    )
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Welcome to PDLS API",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": f"/api/docs" if settings.DEBUG else "Documentation not available in production"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": "2025-11-12T20:00:00Z",
            "version": settings.VERSION
        }
    
    return app


# Create the app instance
app = create_app()


def main():
    """Entry point for development server"""
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
