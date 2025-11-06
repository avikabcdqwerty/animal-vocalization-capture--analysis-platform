import logging
import sys
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware import Middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .auth import get_current_user, AuthError
from .routes.audio_upload import router as audio_upload_router
from .routes.audio_analysis import router as audio_analysis_router
from .routes.species import router as species_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("animal-vocalization-platform")

# Rate limiting: 100 requests/min/user
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Allowed CORS origins (should be configured via env in production)
ALLOWED_ORIGINS = [
    "https://localhost",
    "http://localhost",
    "https://127.0.0.1",
    "http://127.0.0.1",
    # Add production frontend domains here
]

# Trusted hosts (should be configured via env in production)
TRUSTED_HOSTS = ["localhost", "127.0.0.1", "*.yourdomain.com"]

# FastAPI app initialization
app = FastAPI(
    title="Animal Vocalization Capture & Analysis Platform",
    description="A secure, ML-powered web platform for capturing, storing, and analyzing animal vocalizations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Register SlowAPI rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS,
)
# Enforce HTTPS in production (comment out for local dev if needed)
# app.add_middleware(HTTPSRedirectMiddleware)

# Session middleware (if needed for OAuth2 state, CSRF, etc.)
app.add_middleware(
    SessionMiddleware,
    secret_key="REPLACE_WITH_SECURE_RANDOM_KEY",  # Should be set via env var
    https_only=True,
    same_site="lax",
)

# Custom middleware for logging requests and responses
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code} {request.url}")
        return response

app.add_middleware(LoggingMiddleware)

# Global exception handler for authentication errors
@app.exception_handler(AuthError)
async def auth_exception_handler(request: Request, exc: AuthError):
    logger.warning(f"AuthError: {exc.detail} (path: {request.url.path})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for readiness/liveness probes.
    """
    return {"status": "ok"}

# Register API routers
app.include_router(
    audio_upload_router,
    prefix="/api/audio",
    tags=["Audio Upload"],
    dependencies=[],
)
app.include_router(
    audio_analysis_router,
    prefix="/api/analysis",
    tags=["Audio Analysis"],
    dependencies=[],
)
app.include_router(
    species_router,
    prefix="/api/species",
    tags=["Species"],
    dependencies=[],
)

# Export FastAPI app
__all__ = ["app"]