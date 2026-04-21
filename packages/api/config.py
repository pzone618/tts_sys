"""Application configuration management."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_title: str = "TTS System API"
    api_version: str = "v1"
    api_description: str = "Enterprise Text-to-Speech API with multiple engine support"

    # Database
    database_url: str = "sqlite:///./database/tts_sys.db"
    database_echo: bool = False

    # Storage
    storage_path: Path = Path("./storage")
    cache_enabled: bool = True
    cache_max_size_mb: int = 1024
    cache_ttl_days: int = 30

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Edge TTS
    edge_tts_enabled: bool = True

    # Youdao TTS
    youdao_tts_enabled: bool = False
    youdao_app_key: str = ""
    youdao_app_secret: str = ""

    # Azure TTS
    azure_tts_enabled: bool = False
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"

    # Google TTS
    google_tts_enabled: bool = False
    google_application_credentials: str = ""

    # OpenAI TTS
    openai_tts_enabled: bool = False
    openai_api_key: str = ""
    openai_tts_model: str = "tts-1"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    cors_allow_credentials: bool = True

    @property
    def full_api_url_prefix(self) -> str:
        """Get full API URL prefix."""
        return f"/api/{self.api_version}"

    def get_engine_config(self, engine: str) -> dict[str, str]:
        """Get configuration for a specific engine.
        
        Args:
            engine: Engine name (edge, youdao, azure, google, openai)
        
        Returns:
            Configuration dictionary for the engine
        """
        configs = {
            "edge": {},  # Edge TTS requires no config
            "youdao": {
                "app_key": self.youdao_app_key,
                "app_secret": self.youdao_app_secret,
            },
            "azure": {
                "speech_key": self.azure_speech_key,
                "speech_region": self.azure_speech_region,
            },
            "google": {
                "credentials_path": self.google_application_credentials,
            },
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_tts_model,
            },
        }
        return configs.get(engine, {})

    def is_engine_enabled(self, engine: str) -> bool:
        """Check if an engine is enabled.
        
        Args:
            engine: Engine name
        
        Returns:
            True if enabled
        """
        enabled_map = {
            "edge": self.edge_tts_enabled,
            "youdao": self.youdao_tts_enabled,
            "azure": self.azure_tts_enabled,
            "google": self.google_tts_enabled,
            "openai": self.openai_tts_enabled,
        }
        return enabled_map.get(engine, False)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings instance
    """
    return Settings()
