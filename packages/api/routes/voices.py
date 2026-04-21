"""Voice listing routes."""

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

from packages.core.engine_manager import engine_manager
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import ErrorResponse, Voice, VoiceListResponse

router = APIRouter(prefix="/voices", tags=["Voices"])


@router.get(
    "",
    response_model=VoiceListResponse,
    summary="List available voices",
    description="Get list of available voices, optionally filtered by engine, language, or gender",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def list_voices(
    engine: TTSEngine | None = Query(None, description="Filter by engine"),
    language: str | None = Query(None, description="Filter by language code (e.g., en-US)"),
    gender: VoiceGender | None = Query(None, description="Filter by voice gender"),
    search: str | None = Query(None, description="Search in voice name or description"),
) -> VoiceListResponse:
    """List available voices with optional filters.
    
    Args:
        engine: Filter by specific engine
        language: Filter by language code
        gender: Filter by voice gender
        search: Search term for voice name/description
    
    Returns:
        List of matching voices
    """
    try:
        # Get voices
        if engine:
            # Get voices from specific engine
            if not engine_manager.is_engine_available(engine):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Engine not available: {engine.value}",
                )
            engine_instance = engine_manager.get_engine(engine)
            voices = await engine_instance.get_voices(language)
        else:
            # Get voices from all engines
            voices = await engine_manager.get_all_voices(language)

        # Apply gender filter
        if gender:
            voices = [v for v in voices if v.gender == gender]

        # Apply search filter
        if search:
            search_lower = search.lower()
            voices = [
                v
                for v in voices
                if search_lower in v.name.lower()
                or (v.description and search_lower in v.description.lower())
            ]

        logger.info(
            f"Listed voices: total={len(voices)}, "
            f"engine={engine.value if engine else 'all'}, "
            f"language={language or 'all'}"
        )

        return VoiceListResponse(
            voices=voices,
            total=len(voices),
            engine=engine,
            language=language,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list voices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list voices: {str(e)}",
        )


@router.get(
    "/{voice_id}",
    response_model=Voice,
    summary="Get voice details",
    description="Get detailed information about a specific voice",
    responses={
        404: {"model": ErrorResponse, "description": "Voice not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def get_voice(
    voice_id: str,
    engine: TTSEngine | None = Query(None, description="Specify engine to search in"),
) -> Voice:
    """Get details for a specific voice.
    
    Args:
        voice_id: Voice identifier
        engine: Optional engine to limit search
    
    Returns:
        Voice details
    """
    try:
        # Get all voices
        if engine:
            if not engine_manager.is_engine_available(engine):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Engine not available: {engine.value}",
                )
            engine_instance = engine_manager.get_engine(engine)
            voices = await engine_instance.get_voices()
        else:
            voices = await engine_manager.get_all_voices()

        # Find matching voice
        for voice in voices:
            if voice.id == voice_id:
                return voice

        # Not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice not found: {voice_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get voice {voice_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voice: {str(e)}",
        )
