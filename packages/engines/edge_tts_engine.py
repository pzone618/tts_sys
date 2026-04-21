"""Microsoft Edge TTS engine implementation."""

import edge_tts
from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice
from packages.shared.utils import parse_voice_id


class EdgeTTSEngine(TTSEngineBase):
    """Microsoft Edge TTS engine using edge-tts library.
    
    This is a free TTS service that doesn't require API keys.
    """

    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize Edge TTS engine."""
        super().__init__(config)
        self._voices_cache: list[Voice] | None = None

    @property
    def engine_name(self) -> str:
        """Return engine name."""
        return TTSEngine.EDGE.value

    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech using Edge TTS.
        
        Note: Edge TTS generates audio in webm/opus format with fixed quality.
        The quality, bitrate, and sample_rate parameters are logged but do not
        affect the actual audio output from Edge TTS.
        
        Args:
            request: TTS request
        
        Returns:
            Audio data in webm/opus format
        """
        try:
            # Log quality settings (Edge TTS doesn't support custom bitrate/sample_rate)
            quality_info = f"quality={request.quality}" if request.quality else ""
            if request.bitrate or request.sample_rate:
                quality_info += f" (requested bitrate={request.bitrate or 'default'}, sample_rate={request.sample_rate or 'default'})"
            
            # Create communicate object
            communicate = edge_tts.Communicate(
                text=request.text,
                voice=request.voice,
                rate=self._format_rate(request.rate),
                volume=self._format_volume(request.volume),
                pitch=self._format_pitch(request.pitch),
            )

            # Generate audio
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            audio_data = b"".join(audio_chunks)
            logger.info(
                f"Edge TTS synthesis completed: {len(audio_data)} bytes, "
                f"voice={request.voice}, {quality_info}"
            )
            return audio_data

        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            raise RuntimeError(f"Edge TTS synthesis failed: {e}") from e

    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices from Edge TTS.
        
        Args:
            language: Filter by language code (e.g., 'en-US')
        
        Returns:
            List of available voices
        """
        # Use cache if available
        if self._voices_cache is None:
            await self._load_voices()

        if self._voices_cache is None:
            return []

        # Filter by language if specified
        if language:
            return [v for v in self._voices_cache if v.language == language]

        return self._voices_cache

    async def _load_voices(self) -> None:
        """Load voices from Edge TTS and cache them."""
        try:
            # Get voices from edge-tts
            edge_voices = await edge_tts.list_voices()

            # Convert to our Voice model
            voices = []
            for ev in edge_voices:
                # Determine gender
                gender = VoiceGender.NEUTRAL
                if "Male" in ev["Gender"]:
                    gender = VoiceGender.MALE
                elif "Female" in ev["Gender"]:
                    gender = VoiceGender.FEMALE

                # Extract tags
                tags = []
                if "Neural" in ev["ShortName"]:
                    tags.append("neural")
                if ev.get("VoiceType") == "Standard":
                    tags.append("standard")

                # Build description with available fields
                description_parts = []
                if local_name := ev.get("LocalName"):
                    description_parts.append(local_name)
                if voice_type := ev.get("VoiceType"):
                    description_parts.append(voice_type)
                description = " - ".join(description_parts) if description_parts else ev.get("FriendlyName", "")

                voice = Voice(
                    id=ev["ShortName"],
                    name=ev["FriendlyName"],
                    language=ev["Locale"],
                    gender=gender,
                    engine=TTSEngine.EDGE,
                    description=description,
                    tags=tags,
                )
                voices.append(voice)

            self._voices_cache = voices
            logger.info(f"Loaded {len(voices)} voices from Edge TTS")

        except Exception as e:
            logger.error(f"Failed to load Edge TTS voices: {e}")
            self._voices_cache = []

    def _format_rate(self, rate: float) -> str:
        """Format rate for Edge TTS.
        
        Args:
            rate: Rate multiplier (0.5-2.0)
        
        Returns:
            Formatted rate string (e.g., '+50%' or '-25%')
        """
        percentage = int((rate - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        return f"{percentage}%"

    def _format_volume(self, volume: float) -> str:
        """Format volume for Edge TTS.
        
        Args:
            volume: Volume multiplier (0.0-2.0)
        
        Returns:
            Formatted volume string (e.g., '+50%' or '-25%')
        """
        # Edge TTS volume is relative to default (1.0)
        percentage = int((volume - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        return f"{percentage}%"

    def _format_pitch(self, pitch: float) -> str:
        """Format pitch for Edge TTS.
        
        Args:
            pitch: Pitch multiplier (0.5-2.0)
        
        Returns:
            Formatted pitch string (e.g., '+10Hz' or '-10Hz')
        """
        # Edge TTS pitch is in Hz offset
        # Convert multiplier to approximate Hz offset
        hz_offset = int((pitch - 1.0) * 50)
        if hz_offset >= 0:
            return f"+{hz_offset}Hz"
        return f"{hz_offset}Hz"
