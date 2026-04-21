"""FastAPI application entry point."""

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from packages.api.config import get_settings
from packages.api.database import init_db
from packages.api.routes import history, tts, voices
from packages.core.engine_manager import engine_manager
from packages.engines.edge_tts_engine import EdgeTTSEngine
from packages.engines.openai_tts_engine import OpenAITTSEngine
from packages.engines.pyttsx3_engine import Pyttsx3Engine
from packages.engines.youdao_tts_engine import YoudaoTTSEngine
from packages.shared.enums import TTSEngine
from packages.shared.models import HealthResponse
from packages.shared.utils import ensure_directory

settings = get_settings()

# Track application start time
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting TTS System API...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Ensure storage directories exist
    ensure_directory(settings.storage_path)
    ensure_directory(settings.storage_path / "cache")
    ensure_directory(settings.storage_path / "temp")
    logger.info(f"Storage path initialized: {settings.storage_path}")

    # Register and initialize TTS engines
    logger.info("Initializing TTS engines...")

    # Register engine classes
    engine_manager.register_engine_class(TTSEngine.EDGE, EdgeTTSEngine)
    engine_manager.register_engine_class(TTSEngine.YOUDAO, YoudaoTTSEngine)
    engine_manager.register_engine_class(TTSEngine.OPENAI, OpenAITTSEngine)
    engine_manager.register_engine_class(TTSEngine.PYTTSX3, Pyttsx3Engine)

    # Initialize enabled engines
    if settings.is_engine_enabled("edge"):
        engine_manager.initialize_engine(TTSEngine.EDGE)
        logger.info("✓ Edge TTS enabled")

    if settings.is_engine_enabled("youdao"):
        engine_manager.initialize_engine(
            TTSEngine.YOUDAO, settings.get_engine_config("youdao")
        )
        logger.info("✓ Youdao TTS enabled")

    if settings.is_engine_enabled("openai"):
        engine_manager.initialize_engine(
            TTSEngine.OPENAI, settings.get_engine_config("openai")
        )
        logger.info("✓ OpenAI TTS enabled")
    
    # Always enable pyttsx3 as offline fallback
    if settings.is_engine_enabled("pyttsx3"):
        try:
            engine_manager.initialize_engine(TTSEngine.PYTTSX3)
            logger.info("✓ Pyttsx3 TTS enabled (offline fallback)")
        except Exception as e:
            logger.warning(f"Failed to initialize pyttsx3 (optional fallback): {e}")

    available_engines = engine_manager.get_available_engines()
    logger.info(f"✓ {len(available_engines)} TTS engines available")

    logger.info("TTS System API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down TTS System API...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url=f"{settings.full_api_url_prefix}/docs",
    redoc_url=f"{settings.full_api_url_prefix}/redoc",
    openapi_url=f"{settings.full_api_url_prefix}/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tts.router, prefix=settings.full_api_url_prefix)
app.include_router(voices.router, prefix=settings.full_api_url_prefix)
app.include_router(history.router, prefix=settings.full_api_url_prefix)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return JSONResponse(
        {
            "message": "TTS System API",
            "version": settings.api_version,
            "docs_url": f"{settings.full_api_url_prefix}/docs",
        }
    )


@app.get(
    f"{settings.full_api_url_prefix}/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Check API health status."""
    uptime = time.time() - app_start_time

    # Check database
    try:
        from packages.api.database import engine as db_engine

        with db_engine.connect() as conn:
            conn.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Check engines
    engines_status = await engine_manager.health_check_all()

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.api_version,
        uptime_seconds=uptime,
        database=db_status,
        engines=engines_status,
    )


@app.get(
    f"{settings.full_api_url_prefix}/audio/{{filename}}",
    summary="Get audio file",
    tags=["Audio"],
    include_in_schema=False,
)
async def get_audio_file(filename: str):
    """Serve audio files.
    
    Args:
        filename: Audio filename
    
    Returns:
        Audio file response
    """
    # Check in cache directory
    cache_path = settings.storage_path / "cache" / filename
    if cache_path.exists() and cache_path.is_file():
        return FileResponse(
            cache_path,
            media_type="audio/mpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    # Check in temp directory
    temp_path = settings.storage_path / "temp" / filename
    if temp_path.exists() and temp_path.is_file():
        return FileResponse(
            temp_path,
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"},
        )

    return JSONResponse(
        {"error": "File not found", "message": f"Audio file not found: {filename}"},
        status_code=status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        {
            "error": "Internal server error",
            "message": str(exc) if settings.api_debug else "An error occurred",
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "packages.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
