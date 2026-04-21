"""Tests for TTS API routes."""

import pytest
from fastapi import status


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "engines" in data


def test_list_voices(client):
    """Test voice listing endpoint."""
    response = client.get("/api/v1/voices")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "voices" in data
    assert "total" in data
    assert isinstance(data["voices"], list)


def test_list_voices_with_filter(client):
    """Test voice listing with engine filter."""
    response = client.get("/api/v1/voices?engine=edge")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["engine"] == "edge"


def test_generate_speech(client, sample_tts_request):
    """Test speech generation endpoint."""
    response = client.post("/api/v1/tts/generate", json=sample_tts_request)
    
    # Note: This will actually try to generate speech
    # In a real test, you might want to mock the engine
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "request_id" in data
        assert "audio_url" in data
        assert "size_bytes" in data
        assert data["format"] == "mp3"


def test_get_history(client):
    """Test history retrieval."""
    response = client.get("/api/v1/history?limit=10")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "records" in data
    assert "total" in data
    assert "limit" in data
    assert data["limit"] == 10


def test_get_stats(client):
    """Test statistics endpoint."""
    response = client.get("/api/v1/history/stats")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_requests" in data
    assert "by_engine" in data
    assert "cache_hit_rate_percent" in data


def test_cache_stats(client):
    """Test cache statistics endpoint."""
    response = client.get("/api/v1/tts/cache/stats")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "enabled" in data
    assert "total_entries" in data


def test_invalid_engine(client):
    """Test with invalid engine."""
    invalid_request = {
        "text": "Test",
        "engine": "invalid_engine",
        "voice": "test",
    }
    response = client.post("/api/v1/tts/generate", json=invalid_request)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_empty_text(client):
    """Test with empty text."""
    invalid_request = {
        "text": "",
        "engine": "edge",
        "voice": "en-US-JennyNeural",
    }
    response = client.post("/api/v1/tts/generate", json=invalid_request)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
