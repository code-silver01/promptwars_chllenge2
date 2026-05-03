"""
main.py — Election Guide AI Application Entry Point
=====================================================
Bootstraps the FastAPI application with:
  • CORS middleware (origins from environment variable)
  • Security headers middleware
  • Static file serving for the frontend
  • Rate limiter state integration
  • Route registration for /api/chat and /health
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routes.chat import router as chat_router, limiter
from routes.health import router as health_router
from services.gcp_service import init_gcp

# ── Load environment variables from .env (development only) ──
load_dotenv()

# ── Logging configuration ────────────────────────────────────
log_level = logging.DEBUG if os.getenv("ENVIRONMENT") == "development" else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Application lifespan (startup/shutdown events) ───────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    logger.info("🗳️  Election Guide AI starting up...")
    logger.info("Environment: %s", os.getenv("ENVIRONMENT", "production"))
    # Verify critical env vars on startup
    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("⚠️  GEMINI_API_KEY is not set — AI features will fail.")
    
    # Initialize GCP and Firebase for enhanced functionality
    init_gcp()
    yield
    logger.info("🗳️  Election Guide AI shutting down.")


# ── FastAPI app instance ─────────────────────────────────────
app = FastAPI(
    title="Election Guide AI",
    description=(
        "A chat-based AI assistant that helps citizens understand the "
        "election process, check eligibility, register to vote, prepare "
        "documents, and cast their ballot."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Rate limiter integration ────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── CORS middleware ──────────────────────────────────────────
# Origins are loaded from the ALLOWED_ORIGINS environment variable
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080")
allowed_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],      # only methods we actually use
    allow_headers=["Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

from typing import Callable

# ── Security headers middleware ──────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable):
    """
    Inject security headers into every response:
      • X-Content-Type-Options: prevent MIME sniffing
      • X-Frame-Options: prevent clickjacking
      • X-XSS-Protection: legacy XSS filter hint
      • Referrer-Policy: limit referrer leakage
      • Permissions-Policy: restrict browser feature access
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ── Register API routes ──────────────────────────────────────
app.include_router(chat_router)    # POST /api/chat, POST /api/guided-step
app.include_router(health_router)  # GET /health


# ── Static file serving ─────────────────────────────────────
# Mount the static directory for CSS/JS/image assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Root route — serve the frontend SPA ──────────────────────
@app.get(
    "/",
    include_in_schema=False,
    summary="Serve frontend",
)
async def serve_frontend() -> FileResponse:
    """Serve the single-page chat UI."""
    return FileResponse(
        os.path.join(static_dir, "index.html"),
        media_type="text/html",
    )
