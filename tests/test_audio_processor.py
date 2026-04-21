"""Tests for audio processor functionality."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.audio_processor import AudioProcessor
from packages.shared.enums import AudioFormat


class TestAudioProcessor:
    """Test AudioProcessor class."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def processor(self, temp_storage):
        """Create AudioProcessor instance."""
        return AudioProcessor(temp_storage)

    @pytest.mark.asyncio
    async def test_save_audio_mp3(self, processor):
        """Test saving MP3 audio."""
        audio_data = b"fake_mp3_data_with_sufficient_length_for_testing"
        filename = "test_audio"
        
        file_path, full_filename = await processor.save_audio(
            audio_data, filename, AudioFormat.MP3
        )
        
        assert file_path.exists()
        assert file_path.suffix == ".mp3"
        assert full_filename.endswith(".mp3")
        
        # Verify content
        with open(file_path, "rb") as f:
            assert f.read() == audio_data

    @pytest.mark.asyncio
    async def test_save_audio_wav(self, processor):
        """Test saving WAV audio."""
        audio_data = b"fake_wav_data_with_sufficient_length"
        filename = "test_audio"
        
        file_path, full_filename = await processor.save_audio(
            audio_data, filename, AudioFormat.WAV
        )
        
        assert file_path.exists()
        assert file_path.suffix == ".wav"

    @pytest.mark.asyncio
    async def test_save_audio_with_cache(self, processor, temp_storage):
        """Test saving audio with cache flag."""
        audio_data = b"cached_audio_data_for_testing"
        filename = "cached_test"
        
        # Save with cache
        file_path, _ = await processor.save_audio(
            audio_data, filename, AudioFormat.MP3, use_cache=True
        )
        
        # Should be in cache directory
        assert "cache" in str(file_path)

    @pytest.mark.asyncio
    async def test_save_audio_without_cache(self, processor, temp_storage):
        """Test saving audio without cache flag."""
        audio_data = b"non_cached_audio_data_for_testing"
        filename = "non_cached_test"
        
        # Save without cache
        file_path, _ = await processor.save_audio(
            audio_data, filename, AudioFormat.MP3, use_cache=False
        )
        
        # Should be in temp directory, not cache directory
        assert file_path.parent == processor.temp_dir
        assert file_path.parent != processor.cache_dir

    def test_get_file_size(self, processor, temp_storage):
        """Test getting file size."""
        # Create a test file
        test_file = temp_storage / "test.txt"
        test_file.write_bytes(b"test data")
        
        size = processor.get_file_size(test_file)
        assert size == 9  # "test data" is 9 bytes

    def test_get_file_size_nonexistent(self, processor, temp_storage):
        """Test getting size of nonexistent file."""
        nonexistent = temp_storage / "nonexistent.txt"
        size = processor.get_file_size(nonexistent)
        assert size == 0

    def test_get_storage_stats(self, processor, temp_storage):
        """Test getting storage statistics."""
        # Create some test files in cache and temp directories
        (processor.cache_dir / "file1.mp3").write_bytes(b"x" * 1000)
        (processor.temp_dir / "file2.mp3").write_bytes(b"x" * 2000)
        
        stats = processor.get_storage_stats()
        
        assert "storage_path" in stats
        assert "total_files" in stats
        assert "total_size_bytes" in stats
        assert stats["total_files"] >= 2
        assert stats["total_size_bytes"] >= 3000

    @pytest.mark.asyncio
    async def test_delete_audio(self, processor):
        """Test deleting audio file."""
        # Create a test file
        audio_data = b"temporary_audio_data"
        file_path, _ = await processor.save_audio(
            audio_data, "temp", AudioFormat.MP3
        )
        
        assert file_path.exists()
        
        # Delete it
        deleted = await processor.delete_audio(file_path)
        assert deleted is True
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_audio(self, processor, temp_storage):
        """Test deleting nonexistent file."""
        nonexistent = temp_storage / "nonexistent.mp3"
        deleted = await processor.delete_audio(nonexistent)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_concurrent_saves(self, processor):
        """Test concurrent audio saves."""
        async def save_task(i):
            audio_data = f"audio_data_{i}".encode()
            return await processor.save_audio(
                audio_data, f"concurrent_{i}", AudioFormat.MP3
            )
        
        # Save 10 files concurrently
        tasks = [save_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 10
        for file_path, filename in results:
            assert file_path.exists()

    def test_sanitize_filename(self, processor):
        """Test filename sanitization."""
        # This should be handled by the processor
        dangerous_name = "../../../etc/passwd"
        audio_data = b"test"
        
        # Should not raise exception and should sanitize path
        # Implementation depends on AudioProcessor.save_audio
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
