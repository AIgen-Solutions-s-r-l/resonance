"""
Main FastAPI application module.

This module sets up the FastAPI application with all routes and middleware.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    healthcheck_router,
    jobs_matched_router,
    quality_tracking_router
)
from app.core.config import settings
from app.log.logging import logger


try:
    logger.info("Starting application")
    yield
    logger.info("Shutting down application")
except Exception as e:
    logger.error(f"Application lifecycle error: {str(e)}", error=str(e))
    raise



app = FastAPI(
    title="Matching Service API",
    description="API for job-resume matching with quality tracking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routers
app.include_router(healthcheck_router.router, prefix="/api/v1")
app.include_router(jobs_matched_router.router, prefix="/api/v1")
app.include_router(quality_tracking_router.router, prefix="/api/v1")

logger.info("FastAPI application initialized with all routers")


@app.on_event("startup")
async def startup_event():
    """Execute startup tasks."""
    logger.info("Application starting up")
    
    # Initialize database tables
    from app.core.database import engine
    from app.models.quality_tracking import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute shutdown tasks."""
    logger.info("Application shutting down")
    
    # Close any open connections
    from app.core.database import engine
    await engine.dispose()
    
    logger.info("Database connections closed")



@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Matching Service API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }

from app.routers.healthcheck_router import router as healthcheck_router

app.include_router(healthcheck_router)

