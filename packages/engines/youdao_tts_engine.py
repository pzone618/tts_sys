"""Youdao TTS engine implementation."""

import hashlib
import time
import uuid
from typing import Any

import httpx
from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice


class YoudaoTTSEngine(TTSEngineBase):
    """Youdao TTS engine implementation.
    
    Requires Youdao API credentials (app_key and app_secret).
    Documentation: https://ai.youdao.com/DOCSIRMA/html/tts/api/tts/index.html
    """

    API_URL = "https://openapi.youdao.com/ttsapi"

    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize Youdao TTS engine.
        
        Args:
            config: Must include 'app_key' and 'app_secret'
        """
        super().__init__(config)
        self.app_key = self.get_config("app_key")
        self.app_secret = self.get_config("app_secret")

        if not self.app_key or not self.app_secret:
            logger.warning("Youdao TTS: Missing app_key or app_secret")
            self.disable()

    @property
    def engine_name(self) -> str:
        """Return engine name."""
        return TTSEngine.YOUDAO.value

    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech using Youdao TTS.
        
        Note: Youdao TTS uses fixed audio quality settings.
        The quality, bitrate, and sample_rate parameters are logged
        but do not affect the actual audio output.
        
        Args:
            request: TTS request
        
        Returns:
            Audio data in MP3 format
        """
        if not self.is_enabled():
            raise RuntimeError("Youdao TTS engine is not enabled (missing credentials)")

        try:
            # Build request parameters
            params = self._build_request_params(request)

            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.API_URL, data=params)
                response.raise_for_status()

            # Check if response is audio or error
            content_type = response.headers.get("Content-Type", "")
            if "audio" in content_type:
                audio_data = response.content
                quality_info = f"quality={request.quality}" if request.quality else "default"
                logger.info(
                    f"Youdao TTS synthesis completed: {len(audio_data)} bytes, "
                    f"voice={request.voice}, {quality_info}"
                )
                return audio_data
            else:
                # Response is likely JSON error
                error_info = response.json()
                error_msg = error_info.get("errorCode", "Unknown error")
                raise RuntimeError(f"Youdao TTS API error: {error_msg}")

        except httpx.HTTPError as e:
            logger.error(f"Youdao TTS HTTP error: {e}")
            raise RuntimeError(f"Youdao TTS request failed: {e}") from e
        except Exception as e:
            logger.error(f"Youdao TTS synthesis failed: {e}")
            raise RuntimeError(f"Youdao TTS synthesis failed: {e}") from e

    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices for Youdao TTS.
        
        Youdao TTS has limited voice options compared to other engines.
        
        Args:
            language: Filter by language code
        
        Returns:
            List of available voices
        """
        # Youdao predefined voices
        voices = [
            Voice(
                id="0",
                name="度小宇 (Male)",
                language="zh-CN",
                gender=VoiceGender.MALE,
                engine=TTSEngine.YOUDAO,
                description="Standard male voice",
                tags=["chinese", "mandarin"],
            ),
            Voice(
                id="1",
                name="度小美 (Female)",
                language="zh-CN",
                gender=VoiceGender.FEMALE,
                engine=TTSEngine.YOUDAO,
                description="Standard female voice",
                tags=["chinese", "mandarin"],
            ),
            Voice(
                id="3",
                name="度逍遥 (Emotional Male)",
                language="zh-CN",
                gender=VoiceGender.MALE,
                engine=TTSEngine.YOUDAO,
                description="Emotional male voice",
                tags=["chinese", "mandarin", "emotional"],
            ),
            Voice(
                id="4",
                name="度丫丫 (Emotional Female)",
                language="zh-CN",
                gender=VoiceGender.FEMALE,
                engine=TTSEngine.YOUDAO,
                description="Emotional female voice",
                tags=["chinese", "mandarin", "emotional"],
            ),
        ]

        # Filter by language if specified
        if language:
            return [v for v in voices if v.language == language]

        return voices

    def _build_request_params(self, request: TTSRequest) -> dict[str, Any]:
        """Build Youdao API request parameters.
        
        Args:
            request: TTS request
        
        Returns:
            Dictionary of request parameters
        """
        # Generate unique salt and timestamp
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))

        # Build sign string
        sign_str = (
            self.app_key + self._truncate(request.text) + salt + curtime + self.app_secret
        )
        sign = hashlib.sha256(sign_str.encode()).hexdigest()

        # Build parameters
        params = {
            "q": request.text,
            "langType": self._map_voice_to_lang(request.voice),
            "voice": request.voice,
            "format": "mp3",
            "appKey": self.app_key,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime,
            "speed": str(self._format_speed(request.rate)),
            "volume": str(self._format_volume(request.volume)),
        }

        return params

    def _truncate(self, text: str) -> str:
        """Truncate text for sign generation (Youdao requirement).
        
        Args:
            text: Input text
        
        Returns:
            Truncated text
        """
        if len(text) <= 20:
            return text
        return text[:10] + str(len(text)) + text[-10:]

    def _map_voice_to_lang(self, voice: str) -> str:
        """Map voice ID to language type.
        
        Args:
            voice: Voice ID
        
        Returns:
            Language type code
        """
        # For Youdao, all current voices are Chinese
        return "zh-CHS"

    def _format_speed(self, rate: float) -> int:
        """Format rate for Youdao TTS.
        
        Args:
            rate: Rate multiplier (0.5-2.0)
        
        Returns:
            Speed value (-2 to 2)
        """
        # Map 0.5-2.0 to -2 to 2
        speed = int((rate - 1.0) * 2)
        return max(-2, min(2, speed))

    def _format_volume(self, volume: float) -> int:
        """Format volume for Youdao TTS.
        
        Args:
            volume: Volume multiplier (0.0-2.0)
        
        Returns:
            Volume value (0-9)
        """
        # Map 0.0-2.0 to 0-9
        vol = int(volume * 4.5)
        return max(0, min(9, vol))
