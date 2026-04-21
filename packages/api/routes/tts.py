"""TTS synthesis routes."""

import time
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy.orm import Session

from packages.api.config import get_settings
from packages.api.database import TTSRequestRecord, get_db
from packages.core.audio_processor import AudioProcessor
from packages.core.cache_manager import CacheManager
from packages.core.engine_manager import engine_manager
from packages.shared.enums import RequestStatus
from packages.shared.models import ErrorResponse, TTSRequest, TTSResponse
from packages.shared.utils import generate_cache_key

router = APIRouter(prefix="/tts", tags=["TTS"])
settings = get_settings()

# Initialize processors
audio_processor = AudioProcessor(settings.storage_path)
cache_manager = CacheManager(
    settings.storage_path / "cache",
    enabled=settings.cache_enabled,
    ttl_days=settings.cache_ttl_days,
)


@router.post(
    "/generate",
    response_model=TTSResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate speech from text",
    description="Synthesize audio from text using specified TTS engine and voice",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def generate_speech(
    request: TTSRequest,
    db: Session = Depends(get_db),
) -> TTSResponse:
    """Generate speech from text with automatic fallback.
    
    Args:
        request: TTS synthesis request
        db: Database session
    
    Returns:
        TTS response with audio URL and metadata
    """
    start_time = time.time()
    request_id = None
    cached = False
    actual_engine = request.engine
    fallback_occurred = False

    try:
        # Generate cache key (use requested engine for key)
        cache_key = cache_manager.generate_key(request)

        # Try to get from cache
        audio_path = None
        if request.use_cache:
            cached_path = cache_manager.get(cache_key)
            if cached_path:
                audio_path = cached_path
                cached = True
                logger.info(f"Using cached audio: {cache_key}")

        # If not cached, synthesize with fallback
        if not cached:
            logger.info(
                f"Synthesizing with {request.engine.value}: "
                f"text_len={len(request.text)}, voice={request.voice}"
            )

            # Synthesize with automatic fallback
            audio_data, actual_engine, fallback_occurred = (
                await engine_manager.synthesize_with_fallback(request)
            )
            
            if fallback_occurred:
                logger.warning(
                    f"Fallback occurred: requested={request.engine.value}, "
                    f"actual={actual_engine.value}"
                )

            # Save audio file
            filename = f"{cache_key[:16]}"
            audio_path, _ = await audio_processor.save_audio(
                audio_data, filename, request.format, use_cache=request.use_cache
            )

            # Update cache
            if request.use_cache:
                cache_manager.set(
                    cache_key,
                    audio_path,
                    request,
                    len(audio_data),
                )

        # Get file info
        size_bytes = audio_processor.get_file_size(audio_path)
        processing_time = (time.time() - start_time) * 1000

        # Create response with fallback metadata
        response = TTSResponse(
            audio_url=f"/api/{settings.api_version}/audio/{audio_path.name}",
            audio_path=str(audio_path),
            size_bytes=size_bytes,
            format=request.format,
            status=RequestStatus.COMPLETED,
            cached=cached,
            processing_time_ms=processing_time,
            metadata={
                "requested_engine": request.engine.value,
                "actual_engine": actual_engine.value,
                "fallback_occurred": fallback_occurred,
            },
        )

        # Save to database
        db_record = TTSRequestRecord(
            id=str(response.request_id),
            text=request.text[:5000],  # Truncate if too long
            text_hash=cache_key,
            engine=actual_engine.value,  # Save actual engine used
            voice=request.voice,
            rate=request.rate,
            volume=request.volume,
            pitch=request.pitch,
            format=request.format.value,
            audio_path=str(audio_path),
            cache_key=cache_key,
            size_bytes=size_bytes,
            processing_time_ms=processing_time,
            cached=cached,
            status=RequestStatus.COMPLETED.value,
        )
        db.add(db_record)
        db.commit()

        logger.info(
            f"TTS request completed: id={response.request_id}, "
            f"cached={cached}, fallback={fallback_occurred}, "
            f"time={processing_time:.1f}ms"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)

        # Save error to database if request_id exists
        if request_id:
            try:
                db_record = TTSRequestRecord(
                    id=str(request_id),
                    text=request.text[:5000],
                    text_hash=generate_cache_key(
                        request.text, request.engine.value, request.voice
                    ),
                    engine=request.engine.value,
                    voice=request.voice,
                    format=request.format.value,
                    size_bytes=0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    cached=False,
                    status=RequestStatus.FAILED.value,
                    error_message=str(e),
                )
                db.add(db_record)
                db.commit()
            except Exception as db_error:
                logger.error(f"Failed to save error record: {db_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {str(e)}",
        )


@router.get(
    "/cache/stats",
    summary="Get cache statistics",
    description="Get current cache statistics and configuration",
)
async def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        **cache_manager.get_stats(),
        **audio_processor.get_storage_stats(),
    }


@router.delete(
    "/cache/clear",
    summary="Clear TTS cache",
    description="Clear all cached audio files",
)
async def clear_cache() -> dict:
    """Clear TTS cache."""
    count = cache_manager.clear()
    return {"message": f"Cache cleared: {count} entries removed"}


@router.post(
    "/cache/cleanup",
    summary="Clean up expired cache",
    description="Remove expired cache entries based on TTL",
)
async def cleanup_cache() -> dict:
    """Clean up expired cache entries."""
    count = cache_manager.cleanup_expired()
    return {"message": f"Cleanup completed: {count} expired entries removed"}


@router.get(
    "/circuit-breaker/status",
    summary="Get circuit breaker status",
    description="Get current status of circuit breakers for all engines",
)
async def get_circuit_breaker_status() -> dict:
    """Get circuit breaker status for all engines."""
    from packages.core.circuit_breaker import circuit_breaker
    
    stats = circuit_breaker.get_stats()
    
    return {
        "circuit_breakers": stats,
        "available_engines": [e.value for e in engine_manager.get_available_engines()],
        "timestamp": time.time(),
    }


@router.post(
    "/circuit-breaker/reset/{engine_name}",
    summary="Reset circuit breaker",
    description="Manually reset circuit breaker for a specific engine",
)
async def reset_circuit_breaker(engine_name: str) -> dict:
    """Reset circuit breaker for an engine.
    
    Args:
        engine_name: Name of the engine (e.g., "openai", "edge")
    """
    from packages.core.circuit_breaker import circuit_breaker
    
    circuit_breaker.reset(engine_name)
    logger.info(f"Circuit breaker manually reset for: {engine_name}")
    
    return {
        "message": f"Circuit breaker reset for {engine_name}",
        "engine": engine_name,
    }
