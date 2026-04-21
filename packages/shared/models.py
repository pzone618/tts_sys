"""Pydantic models for TTS system."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from .enums import (
    AudioFormat,
    AudioQuality,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_AUDIO_QUALITY,
    DEFAULT_BITRATE,
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_VOLUME,
    MAX_BITRATE,
    MAX_PITCH,
    MAX_RATE,
    MAX_SAMPLE_RATE,
    MAX_TEXT_LENGTH,
    MAX_VOLUME,
    MIN_BITRATE,
    MIN_PITCH,
    MIN_RATE,
    MIN_SAMPLE_RATE,
    MIN_VOLUME,
    QUALITY_BITRATE_MAP,
    QUALITY_SAMPLE_RATE_MAP,
    RequestStatus,
    TTSEngine,
    VoiceGender,
)


class Voice(BaseModel):
    """Voice information model."""

    id: str = Field(..., description="Unique voice identifier")
    name: str = Field(..., description="Human-readable voice name")
    language: str = Field(..., description="Language code (e.g., en-US)")
    gender: VoiceGender = Field(..., description="Voice gender")
    engine: TTSEngine = Field(..., description="TTS engine providing this voice")
    sample_rate: int | None = Field(None, description="Sample rate in Hz")
    description: str | None = Field(None, description="Voice description")
    tags: list[str] = Field(default_factory=list, description="Voice tags/categories")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "en-US-JennyNeural",
                "name": "Jenny (Neural)",
                "language": "en-US",
                "gender": "female",
                "engine": "edge",
                "sample_rate": 24000,
                "description": "Friendly and professional female voice",
                "tags": ["neural", "premium"],
            }
        }


class TTSRequest(BaseModel):
    """TTS synthesis request model."""

    text: str = Field(..., max_length=MAX_TEXT_LENGTH, description="Text to synthesize")
    engine: TTSEngine = Field(..., description="TTS engine to use")
    voice: str = Field(..., description="Voice ID to use")
    rate: float = Field(
        default=DEFAULT_RATE,
        ge=MIN_RATE,
        le=MAX_RATE,
        description="Speech rate (0.5-2.0)",
    )
    volume: float = Field(
        default=DEFAULT_VOLUME,
        ge=MIN_VOLUME,
        le=MAX_VOLUME,
        description="Volume level (0.0-2.0)",
    )
    pitch: float = Field(
        default=DEFAULT_PITCH,
        ge=MIN_PITCH,
        le=MAX_PITCH,
        description="Pitch adjustment (0.5-2.0)",
    )
    format: AudioFormat = Field(
        default=DEFAULT_AUDIO_FORMAT,
        description="Audio output format",
    )
    quality: AudioQuality | None = Field(
        default=None,
        description="Audio quality preset (standard/high/hd). If set, overrides bitrate and sample_rate.",
    )
    bitrate: int | None = Field(
        default=None,
        ge=MIN_BITRATE,
        le=MAX_BITRATE,
        description="Audio bitrate in kbps (32-320). Ignored if quality is set.",
    )
    sample_rate: int | None = Field(
        default=None,
        ge=MIN_SAMPLE_RATE,
        le=MAX_SAMPLE_RATE,
        description="Audio sample rate in Hz (8000-48000). Ignored if quality is set.",
    )
    use_cache: bool = Field(default=True, description="Enable cache lookup")
    
    # Fallback/degradation configuration
    fallback_engines: list[TTSEngine] | None = Field(
        default=None,
        description="Fallback engines to try if primary fails. Leave None for automatic fallback.",
    )
    enable_auto_fallback: bool = Field(
        default=True,
        description="Enable automatic fallback to offline engines when online engines fail",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max retry attempts per engine before falling back",
    )

    def get_effective_bitrate(self) -> int:
        """Get effective bitrate based on quality or explicit setting."""
        if self.quality:
            return QUALITY_BITRATE_MAP.get(self.quality.value, DEFAULT_BITRATE)
        return self.bitrate or DEFAULT_BITRATE
    
    def get_effective_sample_rate(self) -> int:
        """Get effective sample rate based on quality or explicit setting."""
        if self.quality:
            return QUALITY_SAMPLE_RATE_MAP.get(self.quality.value, DEFAULT_SAMPLE_RATE)
        return self.sample_rate or DEFAULT_SAMPLE_RATE

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, this is a test of the TTS system.",
                "engine": "edge",
                "voice": "en-US-JennyNeural",
                "rate": 1.0,
                "volume": 1.0,
                "pitch": 1.0,
                "format": "mp3",
                "quality": "high",
                "bitrate": 192,
                "sample_rate": 24000,
                "use_cache": True,
            }
        }


class TTSResponse(BaseModel):
    """TTS synthesis response model."""

    request_id: UUID = Field(default_factory=uuid4, description="Unique request ID")
    audio_url: str = Field(..., description="URL to access audio file")
    audio_path: str | None = Field(None, description="Local file path (internal)")
    duration_ms: int | None = Field(None, description="Audio duration in milliseconds")
    size_bytes: int = Field(..., description="File size in bytes")
    format: AudioFormat = Field(..., description="Audio format")
    status: RequestStatus = Field(..., description="Request status")
    cached: bool = Field(default=False, description="Whether result was cached")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "audio_url": "/api/v1/audio/550e8400-e29b-41d4-a716-446655440000.mp3",
                "duration_ms": 2500,
                "size_bytes": 48000,
                "format": "mp3",
                "status": "completed",
                "cached": False,
                "processing_time_ms": 342.5,
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class VoiceListRequest(BaseModel):
    """Request model for listing voices."""

    engine: TTSEngine | None = Field(None, description="Filter by engine")
    language: str | None = Field(None, description="Filter by language code")
    gender: VoiceGender | None = Field(None, description="Filter by gender")
    search: str | None = Field(None, description="Search in voice name/description")


class VoiceListResponse(BaseModel):
    """Response model for voice listing."""

    voices: list[Voice] = Field(..., description="List of available voices")
    total: int = Field(..., description="Total number of voices")
    engine: TTSEngine | None = Field(None, description="Filtered engine")
    language: str | None = Field(None, description="Filtered language")


class HistoryRequest(BaseModel):
    """Request model for history query."""

    limit: int = Field(default=50, ge=1, le=500, description="Number of records to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    engine: TTSEngine | None = Field(None, description="Filter by engine")
    status: RequestStatus | None = Field(None, description="Filter by status")
    from_date: datetime | None = Field(None, description="Filter from date")
    to_date: datetime | None = Field(None, description="Filter to date")


class HistoryRecord(BaseModel):
    """History record model."""

    request_id: UUID = Field(..., description="Request ID")
    text: str = Field(..., description="Synthesized text")
    engine: TTSEngine = Field(..., description="Engine used")
    voice: str = Field(..., description="Voice used")
    status: RequestStatus = Field(..., description="Request status")
    size_bytes: int = Field(..., description="File size")
    duration_ms: int | None = Field(None, description="Audio duration")
    processing_time_ms: float = Field(..., description="Processing time")
    cached: bool = Field(..., description="Was cached")
    created_at: datetime = Field(..., description="Creation timestamp")


class HistoryResponse(BaseModel):
    """Response model for history."""

    records: list[HistoryRecord] = Field(..., description="History records")
    total: int = Field(..., description="Total records matching filters")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Service uptime")
    database: str = Field(..., description="Database status")
    engines: dict[str, bool] = Field(..., description="Engine availability")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    request_id: UUID | None = Field(None, description="Request ID if available")
