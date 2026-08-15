import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

    
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import API routers
from app.api.analyzer import router as analyzer_router
from app.api.platform import router as platform_router
from app.api.admin import router as admin_router
from app.services.database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield

app = FastAPI(
    title="CyberShield URL Analyzer API",
    description="""
CyberShield is an intelligent phishing detection platform.

Features:
- URL Validation
- HTTP Analysis
- DNS Analysis
- Domain Intelligence
- SSL/TLS Analysis
- Browser Rendering
- HTML Analysis
- JavaScript Analysis
- Form Analysis
- Reputation Analysis
- Machine Learning Phishing Detection
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React (CRA)
        "http://localhost:5173",   # React (Vite)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ] + ([os.environ["FRONTEND_ORIGIN"].rstrip("/")] if os.environ.get("FRONTEND_ORIGIN") else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routes
app.include_router(analyzer_router)
app.include_router(platform_router)
app.include_router(admin_router)
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint.
    """
    return {
        "project": "CyberShield",
        "service": "URL Threat Intelligence API",
        "version": "1.0.0",
        "status": "Running"
    }


@app.get("/health", tags=["System"])
async def health():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "server": "online"
    }
