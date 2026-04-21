"""Abstract base class for TTS engines."""

from abc import ABC, abstractmethod

from packages.shared.models import TTSRequest, TTSResponse, Voice


class TTSEngineBase(ABC):
    """Abstract base class for TTS engine implementations.
    
    All TTS engines must inherit from this class and implement the required methods.
    """

    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize TTS engine.
        
        Args:
            config: Engine-specific configuration dictionary
        """
        self.config = config or {}
        self.enabled = True

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Return the engine name."""
        pass

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech from text.
        
        Args:
            request: TTS request with text and parameters
        
        Returns:
            Audio data as bytes
        
        Raises:
            Exception: If synthesis fails
        """
        pass

    @abstractmethod
    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices for this engine.
        
        Args:
            language: Filter by language code (e.g., 'en-US'), None for all
        
        Returns:
            List of available voices
        """
        pass

    async def validate_voice(self, voice_id: str, language: str | None = None) -> bool:
        """Validate if a voice ID is available.
        
        Args:
            voice_id: Voice identifier to validate
            language: Optional language filter
        
        Returns:
            True if voice is available
        """
        voices = await self.get_voices(language)
        return any(v.id == voice_id for v in voices)

    async def health_check(self) -> bool:
        """Check if the engine is healthy and operational.
        
        Returns:
            True if engine is healthy
        """
        try:
            # Try to get voices as a simple health check
            voices = await self.get_voices()
            return len(voices) > 0
        except Exception:
            return False

    def is_enabled(self) -> bool:
        """Check if engine is enabled.
        
        Returns:
            True if enabled
        """
        return self.enabled

    def enable(self) -> None:
        """Enable this engine."""
        self.enabled = True

    def disable(self) -> None:
        """Disable this engine."""
        self.enabled = False

    def get_config(self, key: str, default: str | None = None) -> str | None:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def __repr__(self) -> str:
        """String representation of engine."""
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__}(name={self.engine_name}, status={status})>"
