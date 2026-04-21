"""Tests for TTS engines."""

import pytest

from packages.engines.edge_tts_engine import EdgeTTSEngine
from packages.shared.enums import AudioFormat, TTSEngine
from packages.shared.models import TTSRequest


@pytest.mark.asyncio
async def test_edge_tts_get_voices():
    """Test Edge TTS voice listing."""
    engine = EdgeTTSEngine()
    voices = await engine.get_voices()
    
    assert len(voices) > 0
    assert all(v.engine == TTSEngine.EDGE for v in voices)


@pytest.mark.asyncio
async def test_edge_tts_get_voices_filtered():
    """Test Edge TTS voice listing with language filter."""
    engine = EdgeTTSEngine()
    voices = await engine.get_voices(language="en-US")
    
    assert len(voices) > 0
    assert all(v.language == "en-US" for v in voices)


@pytest.mark.asyncio
async def test_edge_tts_synthesize():
    """Test Edge TTS synthesis."""
    engine = EdgeTTSEngine()
    
    request = TTSRequest(
        text="Hello, this is a test.",
        engine=TTSEngine.EDGE,
        voice="en-US-JennyNeural",
        rate=1.0,
        volume=1.0,
        pitch=1.0,
        format=AudioFormat.MP3,
    )
    
    audio_data = await engine.synthesize(request)
    
    assert isinstance(audio_data, bytes)
    assert len(audio_data) > 0


@pytest.mark.asyncio
async def test_edge_tts_health_check():
    """Test Edge TTS health check."""
    engine = EdgeTTSEngine()
    is_healthy = await engine.health_check()
    
    assert is_healthy is True


def test_edge_tts_format_rate():
    """Test rate formatting."""
    engine = EdgeTTSEngine()
    
    assert engine._format_rate(1.0) == "+0%"
    assert engine._format_rate(1.5) == "+50%"
    assert engine._format_rate(0.5) == "-50%"
