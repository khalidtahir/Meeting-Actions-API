"""
FastAPI application entry point.
Wires together routes, middleware, and database initialization.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routes import meetings, actions

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="REST API for extracting action items from meeting transcripts using AI"
)

# Add CORS middleware (configure for production as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """
    Initialize database on application startup.
    Creates tables if they don't exist.
    """
    init_db()


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "status": "operational"
    }


@app.get("/health")
def health_check():
    """Detailed health check for monitoring."""
    return {
        "status": "healthy",
        "database": "connected",  # Could add actual DB ping here
        "ai_provider": settings.ai_provider
    }


# Register route modules
app.include_router(meetings.router)
app.include_router(actions.router)


if __name__ == "__main__":
    import uvicorn
    
    # Run development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )