"""Utility functions for TTS system."""

import hashlib
import re
from pathlib import Path
from typing import Any


def generate_cache_key(text: str, engine: str, voice: str, **params: Any) -> str:
    """Generate a unique cache key for TTS request.
    
    Args:
        text: Text to synthesize
        engine: TTS engine name
        voice: Voice identifier
        **params: Additional parameters (rate, volume, pitch, etc.)
    
    Returns:
        SHA256 hash as cache key
    """
    # Normalize text
    normalized_text = " ".join(text.split())
    
    # Create deterministic string from parameters
    param_str = f"{engine}:{voice}:{normalized_text}"
    for key in sorted(params.keys()):
        param_str += f":{key}={params[key]}"
    
    # Generate hash
    return hashlib.sha256(param_str.encode()).hexdigest()


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum length for filename
    
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    
    # Limit length
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
        max_name_len = max_length - len(ext) - 1
        sanitized = f"{name[:max_name_len]}.{ext}" if ext else name[:max_length]
    
    return sanitized


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
    
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if not.
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_valid_language_code(code: str) -> bool:
    """Validate language code format (e.g., en-US, zh-CN).
    
    Args:
        code: Language code to validate
    
    Returns:
        True if valid format
    """
    pattern = r"^[a-z]{2}-[A-Z]{2}$"
    return bool(re.match(pattern, code))


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append when truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def calculate_duration_from_text(text: str, rate: float = 1.0) -> int:
    """Estimate audio duration from text length.
    
    Rough estimation: ~150 words per minute for English at normal rate.
    
    Args:
        text: Text to synthesize
        rate: Speech rate multiplier
    
    Returns:
        Estimated duration in milliseconds
    """
    word_count = len(text.split())
    base_wpm = 150  # words per minute
    adjusted_wpm = base_wpm * rate
    duration_minutes = word_count / adjusted_wpm
    return int(duration_minutes * 60 * 1000)  # Convert to milliseconds


def parse_voice_id(voice_id: str) -> dict[str, str]:
    """Parse voice ID to extract components.
    
    Common format: language-region-Name or language-Name
    Example: en-US-JennyNeural -> {language: en-US, name: JennyNeural}
    
    Args:
        voice_id: Voice identifier
    
    Returns:
        Dictionary with parsed components
    """
    parts = voice_id.split("-")
    
    if len(parts) >= 3:
        return {
            "language": f"{parts[0]}-{parts[1]}",
            "name": "-".join(parts[2:]),
            "locale": parts[0],
            "region": parts[1],
        }
    elif len(parts) == 2:
        return {
            "language": parts[0],
            "name": parts[1],
            "locale": parts[0],
        }
    else:
        return {
            "name": voice_id,
        }
