"""Enums and constants used throughout the TTS system."""

from enum import Enum


class TTSEngine(str, Enum):
    """Available TTS engines."""

    EDGE = "edge"
    YOUDAO = "youdao"
    AZURE = "azure"
    GOOGLE = "google"
    OPENAI = "openai"
    PYTTSX3 = "pyttsx3"  # Offline local TTS engine (fallback)


class AudioFormat(str, Enum):
    """Supported audio formats."""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    OPUS = "opus"
    AAC = "aac"


class AudioQuality(str, Enum):
    """Audio quality levels."""

    STANDARD = "standard"  # Standard quality, faster processing
    HIGH = "high"          # High quality
    HD = "hd"              # HD quality (if supported by engine)


class VoiceGender(str, Enum):
    """Voice gender categories."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class RequestStatus(str, Enum):
    """TTS request status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class LanguageCode(str, Enum):
    """Common language codes."""

    EN_US = "en-US"
    EN_GB = "en-GB"
    ZH_CN = "zh-CN"
    ZH_TW = "zh-TW"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    ES_ES = "es-ES"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    IT_IT = "it-IT"
    PT_BR = "pt-BR"
    RU_RU = "ru-RU"


# Constants
DEFAULT_RATE = 1.0
DEFAULT_VOLUME = 1.0
DEFAULT_PITCH = 1.0
MIN_RATE = 0.5
MAX_RATE = 2.0
MIN_VOLUME = 0.0
MAX_VOLUME = 2.0
MIN_PITCH = 0.5
MAX_PITCH = 2.0
MAX_TEXT_LENGTH = 5000
DEFAULT_AUDIO_FORMAT = AudioFormat.MP3
DEFAULT_AUDIO_QUALITY = "standard"

# Audio Quality Settings
# Bitrate in kbps
MIN_BITRATE = 32
MAX_BITRATE = 320
DEFAULT_BITRATE = 128
QUALITY_BITRATE_MAP = {
    "standard": 128,  # 128 kbps
    "high": 192,      # 192 kbps
    "hd": 256,        # 256 kbps
}

# Sample Rate in Hz
MIN_SAMPLE_RATE = 8000
MAX_SAMPLE_RATE = 48000
DEFAULT_SAMPLE_RATE = 24000
QUALITY_SAMPLE_RATE_MAP = {
    "standard": 24000,  # 24 kHz
    "high": 24000,      # 24 kHz
    "hd": 48000,        # 48 kHz
}

CACHE_KEY_PREFIX = "tts_cache:"
