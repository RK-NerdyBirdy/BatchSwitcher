"""
Batch Swap Platform - Main Application
A FastAPI-based system for students to swap batches based on CGPA eligibility.

Author: Your Name
Version: 1.0.0
"""
from fastapi import FastAPI,Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import init_db, close_db
from routers import auth, students, swap_requests, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("🚀 Starting Batch Swap Platform...")
    await init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    await close_db()
    print("✅ Cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="Batch Swap Platform API",
    description="API for student batch swapping based on CGPA eligibility",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="batch_swap_session",
    max_age=86400,  # 24 hours
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)


# Include routers
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(swap_requests.router)
app.include_router(chat.router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "message": "Batch Swap Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.head("/")
async def head_root():
    return Response(status_code=200)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "service": "batch-swap-platform"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )