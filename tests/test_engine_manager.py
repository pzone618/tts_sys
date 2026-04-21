"""Tests for engine manager basic functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from packages.core.engine_manager import EngineManager
from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import Voice


class MockTTSEngine(TTSEngineBase):
    """Mock TTS engine for testing."""

    def __init__(self, config=None):
        super().__init__(config)
        self._name = "mock"

    @property
    def engine_name(self) -> str:
        return self._name

    async def synthesize(self, request):
        return b"mock_audio_data"

    async def get_voices(self, language=None):
        return [
            Voice(
                id="mock-voice-1",
                name="Mock Voice 1",
                language="en-US",
                gender=VoiceGender.FEMALE,
                engine=TTSEngine.EDGE,
            )
        ]


class TestEngineManager:
    """Test EngineManager class."""

    def test_initialization(self):
        """Test engine manager initialization."""
        manager = EngineManager()
        assert len(manager._engines) == 0
        assert len(manager._engine_classes) == 0

    def test_register_engine_class(self):
        """Test registering engine class."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        
        assert TTSEngine.EDGE in manager._engine_classes
        assert manager._engine_classes[TTSEngine.EDGE] == MockTTSEngine

    def test_initialize_engine(self):
        """Test initializing engine instance."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        assert TTSEngine.EDGE in manager._engines
        assert isinstance(manager._engines[TTSEngine.EDGE], MockTTSEngine)

    def test_initialize_unregistered_engine(self):
        """Test initializing unregistered engine raises error."""
        manager = EngineManager()
        
        with pytest.raises(ValueError, match="not registered"):
            manager.initialize_engine(TTSEngine.EDGE)

    def test_get_engine(self):
        """Test getting engine instance."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        engine = manager.get_engine(TTSEngine.EDGE)
        assert isinstance(engine, MockTTSEngine)
        assert engine.is_enabled()

    def test_get_disabled_engine(self):
        """Test getting disabled engine raises error."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        # Disable the engine
        manager._engines[TTSEngine.EDGE].disable()
        
        with pytest.raises(ValueError, match="disabled"):
            manager.get_engine(TTSEngine.EDGE)

    def test_get_nonexistent_engine(self):
        """Test getting nonexistent engine raises error."""
        manager = EngineManager()
        
        with pytest.raises(ValueError, match="not initialized"):
            manager.get_engine(TTSEngine.EDGE)

    def test_is_engine_available(self):
        """Test checking engine availability."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        assert manager.is_engine_available(TTSEngine.EDGE) is True
        assert manager.is_engine_available(TTSEngine.OPENAI) is False

    def test_get_available_engines(self):
        """Test getting list of available engines."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.register_engine_class(TTSEngine.OPENAI, MockTTSEngine)
        
        manager.initialize_engine(TTSEngine.EDGE)
        manager.initialize_engine(TTSEngine.OPENAI)
        
        # Disable one
        manager._engines[TTSEngine.OPENAI].disable()
        
        available = manager.get_available_engines()
        assert TTSEngine.EDGE in available
        assert TTSEngine.OPENAI not in available

    @pytest.mark.asyncio
    async def test_get_all_voices(self):
        """Test getting voices from all engines."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        voices = await manager.get_all_voices()
        assert len(voices) > 0
        assert all(isinstance(v, Voice) for v in voices)

    @pytest.mark.asyncio
    async def test_get_all_voices_with_language_filter(self):
        """Test getting voices with language filter."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        voices = await manager.get_all_voices(language="en-US")
        assert all(v.language == "en-US" for v in voices)

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all engines."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        health_status = await manager.health_check_all()
        
        assert isinstance(health_status, dict)
        assert "edge" in health_status
        assert isinstance(health_status["edge"], bool)

    def test_enable_engine(self):
        """Test enabling an engine."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        # Disable first
        manager._engines[TTSEngine.EDGE].disable()
        assert not manager._engines[TTSEngine.EDGE].is_enabled()
        
        # Enable
        manager.enable_engine(TTSEngine.EDGE)
        assert manager._engines[TTSEngine.EDGE].is_enabled()

    def test_disable_engine(self):
        """Test disabling an engine."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        assert manager._engines[TTSEngine.EDGE].is_enabled()
        
        manager.disable_engine(TTSEngine.EDGE)
        assert not manager._engines[TTSEngine.EDGE].is_enabled()

    def test_enable_nonexistent_engine(self):
        """Test enabling nonexistent engine raises error."""
        manager = EngineManager()
        
        with pytest.raises(ValueError, match="not found"):
            manager.enable_engine(TTSEngine.EDGE)

    def test_repr(self):
        """Test string representation."""
        manager = EngineManager()
        manager.register_engine_class(TTSEngine.EDGE, MockTTSEngine)
        manager.initialize_engine(TTSEngine.EDGE)
        
        repr_str = repr(manager)
        assert "EngineManager" in repr_str
        assert "available=" in repr_str
        assert "total=" in repr_str

    def test_multiple_engines(self):
        """Test managing multiple engines."""
        manager = EngineManager()
        
        # Register multiple engines
        for engine_type in [TTSEngine.EDGE, TTSEngine.OPENAI, TTSEngine.YOUDAO]:
            manager.register_engine_class(engine_type, MockTTSEngine)
            manager.initialize_engine(engine_type)
        
        available = manager.get_available_engines()
        assert len(available) == 3

    def test_engine_categorization(self):
        """Test online vs offline engine categorization."""
        manager = EngineManager()
        
        # Test online engines
        assert manager.is_online_engine(TTSEngine.OPENAI) is True
        assert manager.is_online_engine(TTSEngine.YOUDAO) is True
        assert manager.is_online_engine(TTSEngine.AZURE) is True
        
        # Test offline engines
        assert manager.is_online_engine(TTSEngine.EDGE) is False
        assert manager.is_online_engine(TTSEngine.PYTTSX3) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
