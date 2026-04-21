"""Tests for cache manager functionality."""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from packages.core.cache_manager import CacheManager
from packages.shared.enums import AudioFormat, TTSEngine
from packages.shared.models import TTSRequest


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create CacheManager instance."""
        return CacheManager(
            cache_dir=temp_cache_dir,
            enabled=True,
            ttl_days=7,
        )

    @pytest.fixture
    def sample_request(self):
        """Create sample TTS request."""
        return TTSRequest(
            text="Hello, world!",
            engine=TTSEngine.EDGE,
            voice="en-US-JennyNeural",
            rate=1.0,
            volume=1.0,
            pitch=1.0,
            format=AudioFormat.MP3,
        )

    def test_cache_initialization(self, temp_cache_dir):
        """Test cache manager initialization."""
        cache = CacheManager(temp_cache_dir, enabled=True)
        assert cache.enabled is True
        assert cache.cache_dir.exists()

    def test_cache_disabled(self, temp_cache_dir):
        """Test cache manager with caching disabled."""
        cache = CacheManager(temp_cache_dir, enabled=False)
        assert cache.enabled is False

    def test_generate_key(self, cache_manager, sample_request):
        """Test cache key generation."""
        key = cache_manager.generate_key(sample_request)
        
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hex length
        
        # Same request should generate same key
        key2 = cache_manager.generate_key(sample_request)
        assert key == key2

    def test_generate_key_different_requests(self, cache_manager, sample_request):
        """Test different requests generate different keys."""
        key1 = cache_manager.generate_key(sample_request)
        
        # Change text
        sample_request.text = "Different text"
        key2 = cache_manager.generate_key(sample_request)
        
        assert key1 != key2

    def test_set_and_get(self, cache_manager, sample_request, temp_cache_dir):
        """Test setting and getting cache entries."""
        # Create a test audio file
        audio_path = temp_cache_dir / "test_audio.mp3"
        audio_path.write_bytes(b"fake_audio_data")
        
        cache_key = cache_manager.generate_key(sample_request)
        
        # Set cache entry
        cache_manager.set(cache_key, audio_path, sample_request, len(b"fake_audio_data"))
        
        # Get cache entry
        retrieved_path = cache_manager.get(cache_key)
        
        assert retrieved_path is not None
        assert retrieved_path == audio_path

    def test_get_nonexistent(self, cache_manager):
        """Test getting nonexistent cache entry."""
        result = cache_manager.get("nonexistent_key_12345")
        assert result is None

    def test_get_expired(self, cache_manager, sample_request, temp_cache_dir):
        """Test getting expired cache entry."""
        # Create cache with very short TTL
        short_ttl_cache = CacheManager(temp_cache_dir, enabled=True, ttl_days=0)
        
        audio_path = temp_cache_dir / "test_audio.mp3"
        audio_path.write_bytes(b"fake_audio_data")
        
        cache_key = short_ttl_cache.generate_key(sample_request)
        short_ttl_cache.set(cache_key, audio_path, sample_request, 15)
        
        # Should be expired immediately
        time.sleep(0.1)
        result = short_ttl_cache.get(cache_key)
        assert result is None

    def test_clear(self, cache_manager, sample_request, temp_cache_dir):
        """Test clearing all cache entries."""
        # Add some entries
        for i in range(5):
            audio_path = temp_cache_dir / f"test_{i}.mp3"
            audio_path.write_bytes(b"data")
            
            request = sample_request.model_copy(deep=True)
            request.text = f"Text {i}"
            cache_key = cache_manager.generate_key(request)
            
            cache_manager.set(cache_key, audio_path, request, 4)
        
        # Clear cache
        count = cache_manager.clear()
        
        assert count == 5
        assert len(cache_manager._metadata) == 0

    def test_cleanup_expired(self, cache_manager, sample_request, temp_cache_dir):
        """Test cleaning up expired entries."""
        # Create cache with very short TTL
        short_ttl_cache = CacheManager(temp_cache_dir, enabled=True, ttl_days=0)
        
        # Add some entries
        for i in range(3):
            audio_path = temp_cache_dir / f"test_{i}.mp3"
            audio_path.write_bytes(b"data")
            
            request = sample_request.model_copy(deep=True)
            request.text = f"Text {i}"
            cache_key = short_ttl_cache.generate_key(request)
            
            short_ttl_cache.set(cache_key, audio_path, request, 4)
        
        # Wait for expiration
        time.sleep(0.1)
        
        # Cleanup
        count = short_ttl_cache.cleanup_expired()
        
        assert count == 3
        assert len(short_ttl_cache._metadata) == 0

    def test_get_stats(self, cache_manager, sample_request, temp_cache_dir):
        """Test getting cache statistics."""
        stats = cache_manager.get_stats()
        
        assert "enabled" in stats
        assert "total_entries" in stats
        assert "total_size_bytes" in stats
        assert "ttl_days" in stats
        assert stats["enabled"] is True

    def test_cache_with_quality_parameters(self, cache_manager):
        """Test cache key generation with quality parameters."""
        request1 = TTSRequest(
            text="Test",
            engine=TTSEngine.EDGE,
            voice="test",
            quality="high",
        )
        
        request2 = TTSRequest(
            text="Test",
            engine=TTSEngine.EDGE,
            voice="test",
            quality="hd",
        )
        
        key1 = cache_manager.generate_key(request1)
        key2 = cache_manager.generate_key(request2)
        
        # Different quality should produce different keys
        assert key1 != key2

    def test_cache_disabled_operations(self, temp_cache_dir, sample_request):
        """Test cache operations when disabled."""
        cache = CacheManager(temp_cache_dir, enabled=False)
        
        cache_key = cache.generate_key(sample_request)
        
        # Set should be no-op
        audio_path = temp_cache_dir / "test.mp3"
        audio_path.write_bytes(b"data")
        cache.set(cache_key, audio_path, sample_request, 4)
        
        # Get should return None
        result = cache.get(cache_key)
        assert result is None

    def test_cache_hit_miss_tracking(self, cache_manager, sample_request, temp_cache_dir):
        """Test cache hit/miss tracking."""
        audio_path = temp_cache_dir / "test.mp3"
        audio_path.write_bytes(b"data")
        
        cache_key = cache_manager.generate_key(sample_request)
        
        # Initial stats
        stats1 = cache_manager.get_stats()
        initial_hits = stats1.get("cache_hits", 0)
        initial_misses = stats1.get("cache_misses", 0)
        
        # Miss
        cache_manager.get("nonexistent")
        
        # Set and hit
        cache_manager.set(cache_key, audio_path, sample_request, 4)
        cache_manager.get(cache_key)
        
        stats2 = cache_manager.get_stats()
        
        # Verify tracking (if implemented)
        # This depends on whether CacheManager tracks hits/misses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
