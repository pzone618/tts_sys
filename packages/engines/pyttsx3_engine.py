"""Pyttsx3 offline TTS engine implementation.

This engine provides offline text-to-speech using the pyttsx3 library,
which wraps platform-specific TTS engines (SAPI5 on Windows, NSSpeechSynthesizer
on macOS, espeak on Linux).

Use as the ultimate fallback when all online services fail.
"""

import asyncio
import io
import wave
from pathlib import Path

from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice


class Pyttsx3Engine(TTSEngineBase):
    """Pyttsx3 offline TTS engine.
    
    Provides local text-to-speech without requiring network connectivity.
    Quality is lower than cloud services but provides guaranteed availability.
    
    Features:
    - No API keys or network required
    - Multi-platform support
    - Low latency
    - Suitable as ultimate fallback
    
    Limitations:
    - Lower voice quality than cloud services
    - Limited voice selection
    - Platform-dependent voices
    """

    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize pyttsx3 engine.
        
        Args:
            config: Engine configuration (currently unused)
        """
        super().__init__(config)
        self._tts = None
        self._voices_cache: list[Voice] | None = None
        self._initialized = False
        
        # Initialize in a thread since pyttsx3 is synchronous
        try:
            self._init_engine()
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            self.disable()

    def _init_engine(self) -> None:
        """Initialize pyttsx3 engine (synchronous)."""
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            self._initialized = True
            logger.info("pyttsx3 engine initialized successfully")
        except ImportError:
            logger.error(
                "pyttsx3 not installed. Install with: pip install pyttsx3"
            )
            raise
        except Exception as e:
            logger.error(f"pyttsx3 initialization failed: {e}")
            raise

    @property
    def engine_name(self) -> str:
        """Return engine name."""
        return TTSEngine.PYTTSX3.value

    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech using pyttsx3.
        
        Args:
            request: TTS request parameters
            
        Returns:
            Audio data in WAV format
            
        Raises:
            RuntimeError: If engine is not enabled or synthesis fails
        """
        if not self.is_enabled() or not self._initialized:
            raise RuntimeError("pyttsx3 engine is not available")

        try:
            # Run synthesis in thread pool to avoid blocking
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._synthesize_sync,
                request
            )
        except Exception as e:
            logger.error(f"pyttsx3 synthesis failed: {e}")
            raise RuntimeError(f"pyttsx3 synthesis failed: {e}") from e

    def _synthesize_sync(self, request: TTSRequest) -> bytes:
        """Synchronous synthesis implementation.
        
        Args:
            request: TTS request parameters
            
        Returns:
            Audio data in WAV format
        """
        # Configure speech parameters
        # pyttsx3 rate is in words per minute, typically 150-200
        # Our rate is 0.5-2.0, so scale appropriately
        rate = int(request.rate * 175)  # Base rate of 175 wpm
        self._tts.setProperty('rate', rate)
        
        # Volume is 0.0-1.0 for pyttsx3, our range is 0.0-2.0
        volume = min(request.volume / 2.0, 1.0)
        self._tts.setProperty('volume', volume)

        # Set voice if specified and valid
        if request.voice != "default":
            voices = self._tts.getProperty('voices')
            
            # Try to match by index (e.g., "0", "1", "2")
            if request.voice.isdigit():
                voice_index = int(request.voice)
                if 0 <= voice_index < len(voices):
                    self._tts.setProperty('voice', voices[voice_index].id)
            else:
                # Try to match by voice ID or name
                for v in voices:
                    if v.id == request.voice or v.name == request.voice:
                        self._tts.setProperty('voice', v.id)
                        break

        # Create temporary file for output
        # pyttsx3 requires a file path, can't write to BytesIO directly
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Save speech to file
            self._tts.save_to_file(request.text, tmp_path)
            self._tts.runAndWait()

            # Read the file into bytes
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()

            logger.info(
                f"pyttsx3 synthesis completed: {len(audio_data)} bytes, "
                f"rate={rate}, volume={volume:.2f}"
            )

            return audio_data

        finally:
            # Clean up temporary file
            try:
                Path(tmp_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")

    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices from pyttsx3.
        
        Args:
            language: Language filter (not fully supported by pyttsx3)
            
        Returns:
            List of available voices
        """
        if self._voices_cache:
            return self._voices_cache

        if not self._initialized:
            logger.warning("pyttsx3 not initialized, returning empty voice list")
            return []

        try:
            # Run in thread pool
            voices = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_voices_sync
            )
            
            self._voices_cache = voices
            return voices

        except Exception as e:
            logger.error(f"Failed to get pyttsx3 voices: {e}")
            return []

    def _get_voices_sync(self) -> list[Voice]:
        """Get voices synchronously."""
        system_voices = self._tts.getProperty('voices')
        voices = []

        for i, sv in enumerate(system_voices):
            # Parse language from voice properties
            # pyttsx3 voices may have languages list or None
            language = "en-US"  # Default
            if hasattr(sv, 'languages') and sv.languages:
                language = sv.languages[0] if isinstance(sv.languages, list) else str(sv.languages)
            
            # Infer gender from name (basic heuristic)
            gender = VoiceGender.NEUTRAL
            name_lower = sv.name.lower()
            if any(term in name_lower for term in ['female', 'woman', 'girl', 'zira', 'hazel']):
                gender = VoiceGender.FEMALE
            elif any(term in name_lower for term in ['male', 'man', 'boy', 'david', 'mark']):
                gender = VoiceGender.MALE

            voice = Voice(
                id=str(i),  # Use index as ID for simplicity
                name=sv.name,
                language=language,
                gender=gender,
                engine=TTSEngine.PYTTSX3,
                description=f"Local system voice: {sv.name} (offline)",
                tags=["offline", "local", "fallback", "pyttsx3"],
            )
            voices.append(voice)

        logger.info(f"Found {len(voices)} pyttsx3 voices")
        return voices

    async def validate_voice(self, voice_id: str, language: str | None = None) -> bool:
        """Validate if voice is available.
        
        Args:
            voice_id: Voice identifier
            language: Language code (optional)
            
        Returns:
            True if voice is valid
        """
        voices = await self.get_voices()
        return any(v.id == voice_id for v in voices)

    async def health_check(self) -> bool:
        """Check if engine is healthy.
        
        Returns:
            True if engine is operational
        """
        if not self._initialized or not self.is_enabled():
            return False

        try:
            # Simple synthesis test
            test_request = TTSRequest(
                text="Test",
                engine=TTSEngine.PYTTSX3,
                voice="default",
            )
            
            # Try to synthesize a short test
            audio = await self.synthesize(test_request)
            return len(audio) > 0

        except Exception as e:
            logger.error(f"pyttsx3 health check failed: {e}")
            return False
