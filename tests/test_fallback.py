"""Test circuit breaker and fallback functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
from packages.core.engine_manager import EngineManager
from packages.shared.enums import TTSEngine
from packages.shared.models import TTSRequest


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state_closed(self):
        """Test circuit starts in CLOSED state."""
        breaker = CircuitBreaker()
        assert breaker.get_state("test_engine") == CircuitState.CLOSED
        assert breaker.is_available("test_engine") is True

    def test_open_circuit_after_failures(self):
        """Test circuit opens after reaching failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout_seconds=60)
        breaker = CircuitBreaker(config)

        # Record failures
        for _ in range(3):
            breaker.record_failure("test_engine")

        assert breaker.get_state("test_engine") == CircuitState.OPEN
        assert breaker.is_available("test_engine") is False

    def test_circuit_recovery(self):
        """Test circuit transitions to HALF_OPEN and recovers."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1,  # Very short timeout for testing
        )
        breaker = CircuitBreaker(config)

        # Open circuit
        breaker.record_failure("test_engine")
        breaker.record_failure("test_engine")
        assert breaker.get_state("test_engine") == CircuitState.OPEN

        # Wait for timeout
        import time
        time.sleep(0.2)

        # Should transition to HALF_OPEN
        assert breaker.get_state("test_engine") == CircuitState.HALF_OPEN

        # Record successes
        breaker.record_success("test_engine")
        breaker.record_success("test_engine")

        # Should be CLOSED now
        assert breaker.get_state("test_engine") == CircuitState.CLOSED
        assert breaker.is_available("test_engine") is True

    def test_half_open_reopens_on_failure(self):
        """Test HALF_OPEN reopens immediately on failure."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,
        )
        breaker = CircuitBreaker(config)

        # Open circuit
        breaker.record_failure("test_engine")
        breaker.record_failure("test_engine")

        # Wait for HALF_OPEN
        import time
        time.sleep(0.2)
        assert breaker.get_state("test_engine") == CircuitState.HALF_OPEN

        # Fail again - should reopen
        breaker.record_failure("test_engine")
        assert breaker.get_state("test_engine") == CircuitState.OPEN

    def test_reset_circuit(self):
        """Test manual circuit reset."""
        breaker = CircuitBreaker()

        # Open circuit
        for _ in range(5):
            breaker.record_failure("test_engine")

        assert breaker.get_state("test_engine") == CircuitState.OPEN

        # Reset
        breaker.reset("test_engine")
        assert breaker.get_state("test_engine") == CircuitState.CLOSED

    def test_get_stats(self):
        """Test getting circuit breaker stats."""
        breaker = CircuitBreaker()

        breaker.record_failure("engine1")
        breaker.record_success("engine2")

        stats = breaker.get_stats()

        assert "engine1" in stats
        assert "engine2" in stats
        assert stats["engine1"]["failure_count"] == 1
        assert stats["engine2"]["success_count"] == 1


class TestEngineFallback:
    """Test engine fallback functionality."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock engine."""
        engine = MagicMock()
        engine.is_enabled.return_value = True
        engine.synthesize = AsyncMock(return_value=b"fake_audio_data")
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        """Create engine manager with mock engines."""
        manager = EngineManager()
        
        # Mock the engines dict
        manager._engines = {
            TTSEngine.OPENAI: mock_engine,
            TTSEngine.EDGE: mock_engine,
            TTSEngine.PYTTSX3: mock_engine,
        }
        
        return manager

    def test_get_fallback_chain_default(self, manager):
        """Test default fallback chain generation."""
        # For online engine, should fallback to other online then offline
        chain = manager.get_fallback_chain(TTSEngine.OPENAI)
        
        assert chain[0] == TTSEngine.OPENAI  # Primary
        assert TTSEngine.EDGE in chain  # Offline fallback
        assert TTSEngine.PYTTSX3 in chain  # Offline fallback

    def test_get_fallback_chain_custom(self, manager):
        """Test custom fallback chain."""
        chain = manager.get_fallback_chain(
            TTSEngine.OPENAI,
            custom_fallbacks=[TTSEngine.PYTTSX3]
        )
        
        assert chain == [TTSEngine.OPENAI, TTSEngine.PYTTSX3]

    @pytest.mark.asyncio
    async def test_synthesize_with_fallback_success(self, manager, mock_engine):
        """Test successful synthesis without fallback."""
        request = TTSRequest(
            text="Hello",
            engine=TTSEngine.OPENAI,
            voice="alloy",
        )

        audio, actual_engine, fallback_occurred = await manager.synthesize_with_fallback(request)

        assert audio == b"fake_audio_data"
        assert actual_engine == TTSEngine.OPENAI
        assert fallback_occurred is False

    @pytest.mark.asyncio
    async def test_synthesize_with_fallback_triggers(self, manager):
        """Test fallback triggers when primary fails."""
        # Mock engines to fail then succeed
        openai_engine = MagicMock()
        openai_engine.is_enabled.return_value = True
        openai_engine.synthesize = AsyncMock(side_effect=RuntimeError("OpenAI failed"))

        edge_engine = MagicMock()
        edge_engine.is_enabled.return_value = True
        edge_engine.synthesize = AsyncMock(return_value=b"edge_audio")

        manager._engines = {
            TTSEngine.OPENAI: openai_engine,
            TTSEngine.EDGE: edge_engine,
        }

        request = TTSRequest(
            text="Hello",
            engine=TTSEngine.OPENAI,
            voice="alloy",
            enable_auto_fallback=True,
            max_retries=0,  # No retries for faster test
        )

        # Mock voice mapping
        with patch.object(manager, '_map_voice_for_engine', new_callable=AsyncMock) as mock_map:
            mock_map.return_value = "en-US-JennyNeural"

            audio, actual_engine, fallback_occurred = await manager.synthesize_with_fallback(request)

            assert audio == b"edge_audio"
            assert actual_engine == TTSEngine.EDGE
            assert fallback_occurred is True

    @pytest.mark.asyncio
    async def test_synthesize_all_engines_fail(self, manager):
        """Test exception when all engines fail."""
        failing_engine = MagicMock()
        failing_engine.is_enabled.return_value = True
        failing_engine.synthesize = AsyncMock(side_effect=RuntimeError("Failed"))

        manager._engines = {
            TTSEngine.OPENAI: failing_engine,
            TTSEngine.EDGE: failing_engine,
        }

        request = TTSRequest(
            text="Hello",
            engine=TTSEngine.OPENAI,
            voice="alloy",
            max_retries=0,
        )

        with pytest.raises(RuntimeError, match="All engines failed"):
            await manager.synthesize_with_fallback(request)

    @pytest.mark.asyncio
    async def test_fallback_disabled(self, manager, mock_engine):
        """Test fallback can be disabled."""
        manager._engines = {TTSEngine.OPENAI: mock_engine}

        request = TTSRequest(
            text="Hello",
            engine=TTSEngine.OPENAI,
            voice="alloy",
            enable_auto_fallback=False,
        )

        audio, actual_engine, fallback_occurred = await manager.synthesize_with_fallback(request)

        assert actual_engine == TTSEngine.OPENAI
        assert fallback_occurred is False

    def test_is_online_engine(self, manager):
        """Test engine categorization."""
        assert manager.is_online_engine(TTSEngine.OPENAI) is True
        assert manager.is_online_engine(TTSEngine.YOUDAO) is True
        assert manager.is_online_engine(TTSEngine.EDGE) is False
        assert manager.is_online_engine(TTSEngine.PYTTSX3) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
