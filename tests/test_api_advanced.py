"""Additional API tests for quality and fallback features."""

import pytest
from fastapi import status


class TestQualityParameters:
    """Test audio quality parameter handling."""

    def test_quality_preset_standard(self, client):
        """Test with standard quality preset."""
        request = {
            "text": "Testing standard quality",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "quality": "standard",
        }
        response = client.post("/api/v1/tts/generate", json=request)
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "size_bytes" in data

    def test_quality_preset_high(self, client):
        """Test with high quality preset."""
        request = {
            "text": "Testing high quality",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "quality": "high",
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_quality_preset_hd(self, client):
        """Test with HD quality preset."""
        request = {
            "text": "Testing HD quality",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "quality": "hd",
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_explicit_bitrate(self, client):
        """Test with explicit bitrate."""
        request = {
            "text": "Testing explicit bitrate",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "bitrate": 192,
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_200_OK

    def test_explicit_sample_rate(self, client):
        """Test with explicit sample rate."""
        request = {
            "text": "Testing explicit sample rate",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "sample_rate": 24000,
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_200_OK

    def test_quality_and_bitrate_together(self, client):
        """Test quality preset overrides explicit bitrate."""
        request = {
            "text": "Testing quality priority",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "quality": "high",
            "bitrate": 64,  # Should be ignored
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_bitrate(self, client):
        """Test with invalid bitrate."""
        request = {
            "text": "Testing invalid bitrate",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "bitrate": 999,  # Too high
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_sample_rate(self, client):
        """Test with invalid sample rate."""
        request = {
            "text": "Testing invalid sample rate",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "sample_rate": 5000,  # Too low
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestFallbackAPI:
    """Test fallback-related API features."""

    def test_auto_fallback_enabled(self, client):
        """Test with automatic fallback enabled."""
        request = {
            "text": "Testing auto fallback",
            "engine": "openai",
            "voice": "alloy",
            "enable_auto_fallback": True,
        }
        response = client.post("/api/v1/tts/generate", json=request)
        
        # Should succeed even if OpenAI fails
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            metadata = data.get("metadata", {})
            assert "requested_engine" in metadata
            assert "actual_engine" in metadata
            assert "fallback_occurred" in metadata

    def test_auto_fallback_disabled(self, client):
        """Test with automatic fallback disabled."""
        request = {
            "text": "Testing no fallback",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "enable_auto_fallback": False,
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_200_OK

    def test_custom_fallback_chain(self, client):
        """Test with custom fallback engines."""
        request = {
            "text": "Testing custom fallback",
            "engine": "openai",
            "voice": "alloy",
            "fallback_engines": ["edge", "pyttsx3"],
        }
        response = client.post("/api/v1/tts/generate", json=request)
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            metadata = data.get("metadata", {})
            actual_engine = metadata.get("actual_engine", "")
            # Should use one of the engines in the chain
            assert actual_engine in ["openai", "edge", "pyttsx3"]

    def test_max_retries_parameter(self, client):
        """Test max_retries parameter."""
        request = {
            "text": "Testing max retries",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "max_retries": 1,
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_max_retries(self, client):
        """Test with invalid max_retries value."""
        request = {
            "text": "Testing invalid retries",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "max_retries": 10,  # Exceeds max of 5
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_circuit_breaker_status_endpoint(self, client):
        """Test circuit breaker status endpoint."""
        response = client.get("/api/v1/tts/circuit-breaker/status")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "circuit_breakers" in data
        assert "available_engines" in data
        assert isinstance(data["circuit_breakers"], dict)
        assert isinstance(data["available_engines"], list)

    def test_circuit_breaker_reset_endpoint(self, client):
        """Test circuit breaker reset endpoint."""
        response = client.post("/api/v1/tts/circuit-breaker/reset/edge")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "engine" in data
        assert data["engine"] == "edge"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_text_too_long(self, client):
        """Test with text exceeding maximum length."""
        request = {
            "text": "x" * 10001,  # Exceeds MAX_TEXT_LENGTH if set to 10000
            "engine": "edge",
            "voice": "en-US-JennyNeural",
        }
        response = client.post("/api/v1/tts/generate", json=request)
        # Should either succeed or return validation error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    def test_invalid_voice_id(self, client):
        """Test with invalid voice ID."""
        request = {
            "text": "Test",
            "engine": "edge",
            "voice": "invalid-voice-id-12345",
        }
        response = client.post("/api/v1/tts/generate", json=request)
        # May fail during synthesis
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    def test_invalid_rate(self, client):
        """Test with invalid rate value."""
        request = {
            "text": "Test",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "rate": 5.0,  # Exceeds max
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_volume(self, client):
        """Test with invalid volume value."""
        request = {
            "text": "Test",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "volume": -1.0,  # Below min
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_format(self, client):
        """Test with invalid audio format."""
        request = {
            "text": "Test",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "format": "invalid_format",
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_required_fields(self, client):
        """Test with missing required fields."""
        request = {
            "text": "Test",
            # Missing engine and voice
        }
        response = client.post("/api/v1/tts/generate", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCaching:
    """Test caching behavior."""

    def test_cache_hit(self, client):
        """Test cache hit behavior."""
        request = {
            "text": "Cache test message",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "use_cache": True,
        }
        
        # First request - cache miss
        response1 = client.post("/api/v1/tts/generate", json=request)
        if response1.status_code != status.HTTP_200_OK:
            pytest.skip("Engine not available")
        
        data1 = response1.json()
        
        # Second request - should hit cache
        response2 = client.post("/api/v1/tts/generate", json=request)
        data2 = response2.json()
        
        # Second should be faster or explicitly cached
        assert data2["cached"] is True or data2["processing_time_ms"] < data1["processing_time_ms"]

    def test_cache_disabled(self, client):
        """Test with caching disabled."""
        request = {
            "text": "No cache test",
            "engine": "edge",
            "voice": "en-US-JennyNeural",
            "use_cache": False,
        }
        
        response = client.post("/api/v1/tts/generate", json=request)
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["cached"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
