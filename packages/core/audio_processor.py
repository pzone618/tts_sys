"""Audio file processing and management."""

import hashlib
from pathlib import Path
from typing import BinaryIO

import aiofiles
from loguru import logger

from packages.shared.enums import AudioFormat
from packages.shared.utils import ensure_directory, sanitize_filename


class AudioProcessor:
    """Handles audio file operations and storage."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize audio processor.
        
        Args:
            storage_path: Base path for audio storage
        """
        self.storage_path = storage_path
        self.cache_dir = storage_path / "cache"
        self.temp_dir = storage_path / "temp"

        # Ensure directories exist
        ensure_directory(self.cache_dir)
        ensure_directory(self.temp_dir)

    async def save_audio(
        self,
        audio_data: bytes,
        filename: str,
        format: AudioFormat = AudioFormat.MP3,
        use_cache: bool = True,
    ) -> tuple[Path, str]:
        """Save audio data to file.
        
        Args:
            audio_data: Audio bytes
            filename: Desired filename (without extension)
            format: Audio format
            use_cache: Save to cache directory
        
        Returns:
            Tuple of (file_path, full_filename)
        """
        # Sanitize filename and add extension
        safe_filename = sanitize_filename(filename)
        full_filename = f"{safe_filename}.{format.value}"

        # Determine save directory
        save_dir = self.cache_dir if use_cache else self.temp_dir
        file_path = save_dir / full_filename

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(audio_data)

        logger.info(f"Saved audio file: {file_path} ({len(audio_data)} bytes)")
        return file_path, full_filename

    async def load_audio(self, file_path: Path) -> bytes:
        """Load audio file.
        
        Args:
            file_path: Path to audio file
        
        Returns:
            Audio data as bytes
        
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        async with aiofiles.open(file_path, "rb") as f:
            audio_data = await f.read()

        logger.debug(f"Loaded audio file: {file_path} ({len(audio_data)} bytes)")
        return audio_data

    async def delete_audio(self, file_path: Path) -> bool:
        """Delete audio file.
        
        Args:
            file_path: Path to file to delete
        
        Returns:
            True if deleted successfully
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted audio file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete audio file {file_path}: {e}")
            return False

    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes.
        
        Args:
            file_path: Path to file
        
        Returns:
            File size in bytes
        """
        return file_path.stat().st_size if file_path.exists() else 0

    def find_cached_file(self, cache_key: str, format: AudioFormat) -> Path | None:
        """Find cached audio file by cache key.
        
        Args:
            cache_key: Cache key (hash)
            format: Audio format
        
        Returns:
            Path to cached file or None
        """
        # Search for file with matching hash in name
        pattern = f"*{cache_key[:16]}*.{format.value}"
        matches = list(self.cache_dir.glob(pattern))

        if matches:
            return matches[0]
        
        # Also check exact cache key filename
        exact_path = self.cache_dir / f"{cache_key}.{format.value}"
        if exact_path.exists():
            return exact_path

        return None

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours
        
        Returns:
            Number of files deleted
        """
        from datetime import datetime, timedelta

        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        await self.delete_audio(file_path)
                        deleted_count += 1
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")

        logger.info(f"Cleaned up {deleted_count} temporary files")
        return deleted_count

    def get_storage_stats(self) -> dict[str, int | str]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        cache_files = list(self.cache_dir.iterdir())
        temp_files = list(self.temp_dir.iterdir())

        cache_size = sum(f.stat().st_size for f in cache_files if f.is_file())
        temp_size = sum(f.stat().st_size for f in temp_files if f.is_file())

        return {
            "storage_path": str(self.storage_path),
            "cache_files": len(cache_files),
            "cache_size_bytes": cache_size,
            "temp_files": len(temp_files),
            "temp_size_bytes": temp_size,
            "total_files": len(cache_files) + len(temp_files),
            "total_size_bytes": cache_size + temp_size,
        }
