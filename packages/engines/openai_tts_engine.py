"""OpenAI TTS engine implementation."""

import httpx
from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice


class OpenAITTSEngine(TTSEngineBase):
    """OpenAI TTS engine implementation.
    
    Requires OpenAI API key.
    Documentation: https://platform.openai.com/docs/guides/text-to-speech
    """

    API_URL = "https://api.openai.com/v1/audio/speech"
    DEFAULT_MODEL = "tts-1"
    HD_MODEL = "tts-1-hd"

    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize OpenAI TTS engine.
        
        Args:
            config: Must include 'api_key', optional 'model'
        """
        super().__init__(config)
        self.api_key = self.get_config("api_key")
        self.model = self.get_config("model", self.DEFAULT_MODEL)

        if not self.api_key:
            logger.warning("OpenAI TTS: Missing api_key")
            self.disable()

    @property
    def engine_name(self) -> str:
        """Return engine name."""
        return TTSEngine.OPENAI.value

    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech using OpenAI TTS.
        
        The quality parameter affects model selection:
        - 'standard' or 'high': Uses tts-1 (faster, lower latency)
        - 'hd': Uses tts-1-hd (higher quality, slightly higher latency)
        
        Args:
            request: TTS request
        
        Returns:
            Audio data in MP3/OPUS/AAC/FLAC format
        """
        if not self.is_enabled():
            raise RuntimeError("OpenAI TTS engine is not enabled (missing API key)")

        try:
            # Determine model based on quality setting
            model = self._select_model(request)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Map our format to OpenAI's supported formats
            response_format = self._map_format(request.format.value)

            payload = {
                "model": model,
                "input": request.text,
                "voice": request.voice,
                "response_format": response_format,
                "speed": request.rate,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.API_URL, headers=headers, json=payload)
                response.raise_for_status()

            audio_data = response.content
            quality_info = f"quality={request.quality}" if request.quality else "default"
            logger.info(
                f"OpenAI TTS synthesis completed: {len(audio_data)} bytes, "
                f"voice={request.voice}, model={model}, {quality_info}"
            )
            return audio_data

        except httpx.HTTPError as e:
            logger.error(f"OpenAI TTS HTTP error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"OpenAI API error detail: {error_detail}")
                except Exception:
                    pass
            raise RuntimeError(f"OpenAI TTS request failed: {e}") from e
        except Exception as e:
            logger.error(f"OpenAI TTS synthesis failed: {e}")
            raise RuntimeError(f"OpenAI TTS synthesis failed: {e}") from e
    
    def _select_model(self, request: TTSRequest) -> str:
        """Select OpenAI TTS model based on quality settings.
        
        Args:
            request: TTS request with quality settings
            
        Returns:
            Model name (tts-1 or tts-1-hd)
        """
        # If quality is explicitly set to 'hd', use HD model
        if request.quality and request.quality.value == "hd":
            return self.HD_MODEL
        
        # Otherwise use standard model (faster)
        return self.DEFAULT_MODEL

    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices for OpenAI TTS.
        
        OpenAI provides 6 built-in voices: alloy, echo, fable, onyx, nova, shimmer
        
        Args:
            language: Not used (OpenAI voices support multiple languages)
        
        Returns:
            List of available voices
        """
        voices = [
            Voice(
                id="alloy",
                name="Alloy",
                language="en-US",
                gender=VoiceGender.NEUTRAL,
                engine=TTSEngine.OPENAI,
                description="Neutral voice, suitable for various content",
                tags=["multilingual", "neural"],
            ),
            Voice(
                id="echo",
                name="Echo",
                language="en-US",
                gender=VoiceGender.MALE,
                engine=TTSEngine.OPENAI,
                description="Male voice with clear pronunciation",
                tags=["multilingual", "neural"],
            ),
            Voice(
                id="fable",
                name="Fable",
                language="en-US",
                gender=VoiceGender.MALE,
                engine=TTSEngine.OPENAI,
                description="Male voice for storytelling",
                tags=["multilingual", "neural", "expressive"],
            ),
            Voice(
                id="onyx",
                name="Onyx",
                language="en-US",
                gender=VoiceGender.MALE,
                engine=TTSEngine.OPENAI,
                description="Deep male voice",
                tags=["multilingual", "neural"],
            ),
            Voice(
                id="nova",
                name="Nova",
                language="en-US",
                gender=VoiceGender.FEMALE,
                engine=TTSEngine.OPENAI,
                description="Energetic female voice",
                tags=["multilingual", "neural"],
            ),
            Voice(
                id="shimmer",
                name="Shimmer",
                language="en-US",
                gender=VoiceGender.FEMALE,
                engine=TTSEngine.OPENAI,
                description="Soft female voice",
                tags=["multilingual", "neural"],
            ),
        ]

        return voices

    def _map_format(self, format: str) -> str:
        """Map our audio format to OpenAI's supported formats.
        
        OpenAI supports: mp3, opus, aac, flac
        
        Args:
            format: Our audio format
        
        Returns:
            OpenAI format string
        """
        format_map = {
            "mp3": "mp3",
            "opus": "opus",
            "aac": "aac",
            "wav": "mp3",  # Fallback to mp3
            "ogg": "opus",  # Use opus for ogg
        }
        return format_map.get(format, "mp3")
