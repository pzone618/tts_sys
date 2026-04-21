"""Cache management for TTS requests."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from packages.shared.enums import AudioFormat
from packages.shared.models import TTSRequest
from packages.shared.utils import generate_cache_key


class CacheManager:
    """Manages caching of TTS requests and responses."""

    def __init__(
        self, cache_dir: Path, enabled: bool = True, ttl_days: int = 30
    ) -> None:
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage
            enabled: Whether caching is enabled
            ttl_days: Time to live for cache entries in days
        """
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.ttl_days = ttl_days
        self.metadata_file = cache_dir / "cache_metadata.json"
        self._metadata: dict[str, dict[str, Any]] = {}

        # Load metadata
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
                logger.info(f"Loaded cache metadata with {len(self._metadata)} entries")
            except Exception as e:
                logger.error(f"Failed to load cache metadata: {e}")
                self._metadata = {}
        else:
            self._metadata = {}

    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def generate_key(self, request: TTSRequest) -> str:
        """Generate cache key for TTS request.
        
        Args:
            request: TTS request
        
        Returns:
            Cache key (hash)
        """
        return generate_cache_key(
            text=request.text,
            engine=request.engine.value,
            voice=request.voice,
            rate=request.rate,
            volume=request.volume,
            pitch=request.pitch,
            format=request.format.value,
            quality=request.quality.value if request.quality else None,
            bitrate=request.bitrate,
            sample_rate=request.sample_rate,
        )

    def get(self, cache_key: str) -> Path | None:
        """Get cached audio file path if valid.
        
        Args:
            cache_key: Cache key
        
        Returns:
            Path to cached file or None
        """
        if not self.enabled:
            return None

        # Check if entry exists in metadata
        if cache_key not in self._metadata:
            return None

        entry = self._metadata[cache_key]
        file_path = Path(entry["file_path"])

        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Cached file not found: {file_path}")
            self._remove_entry(cache_key)
            return None

        # Check TTL
        created_at = datetime.fromisoformat(entry["created_at"])
        if datetime.utcnow() - created_at > timedelta(days=self.ttl_days):
            logger.info(f"Cache entry expired: {cache_key}")
            self._remove_entry(cache_key)
            return None

        # Update last accessed time
        entry["last_accessed"] = datetime.utcnow().isoformat()
        entry["access_count"] = entry.get("access_count", 0) + 1
        self._save_metadata()

        logger.debug(f"Cache hit: {cache_key}")
        return file_path

    def set(
        self,
        cache_key: str,
        file_path: Path,
        request: TTSRequest,
        size_bytes: int,
        duration_ms: int | None = None,
    ) -> None:
        """Store cache entry metadata.
        
        Args:
            cache_key: Cache key
            file_path: Path to audio file
            request: Original TTS request
            size_bytes: File size in bytes
            duration_ms: Audio duration in milliseconds
        """
        if not self.enabled:
            return

        self._metadata[cache_key] = {
            "file_path": str(file_path),
            "text": request.text[:100],  # Store first 100 chars for reference
            "engine": request.engine.value,
            "voice": request.voice,
            "format": request.format.value,
            "size_bytes": size_bytes,
            "duration_ms": duration_ms,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "access_count": 0,
        }

        self._save_metadata()
        logger.debug(f"Cache set: {cache_key}")

    def _remove_entry(self, cache_key: str) -> None:
        """Remove cache entry from metadata.
        
        Args:
            cache_key: Cache key to remove
        """
        if cache_key in self._metadata:
            # Also try to delete the file
            try:
                file_path = Path(self._metadata[cache_key]["file_path"])
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete cached file: {e}")

            del self._metadata[cache_key]
            self._save_metadata()

    def invalidate(self, cache_key: str) -> bool:
        """Invalidate a cache entry.
        
        Args:
            cache_key: Cache key to invalidate
        
        Returns:
            True if entry was invalidated
        """
        if cache_key in self._metadata:
            self._remove_entry(cache_key)
            logger.info(f"Cache invalidated: {cache_key}")
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = len(self._metadata)

        # Delete all cached files
        for entry in self._metadata.values():
            try:
                file_path = Path(entry["file_path"])
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete cached file: {e}")

        self._metadata = {}
        self._save_metadata()

        logger.info(f"Cache cleared: {count} entries")
        return count

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        expired_keys = []
        cutoff = datetime.utcnow() - timedelta(days=self.ttl_days)

        for key, entry in self._metadata.items():
            created_at = datetime.fromisoformat(entry["created_at"])
            if created_at < cutoff:
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_entry(key)

        logger.info(f"Removed {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self._metadata)
        total_size = sum(e.get("size_bytes", 0) for e in self._metadata.values())
        total_accesses = sum(e.get("access_count", 0) for e in self._metadata.values())

        return {
            "enabled": self.enabled,
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_accesses": total_accesses,
            "ttl_days": self.ttl_days,
            "avg_size_bytes": total_size / total_entries if total_entries > 0 else 0,
        }
