"""Tests for utility functions."""

from packages.shared.utils import (
    calculate_duration_from_text,
    format_file_size,
    generate_cache_key,
    is_valid_language_code,
    parse_voice_id,
    sanitize_filename,
    truncate_text,
)


def test_generate_cache_key():
    """Test cache key generation."""
    key1 = generate_cache_key("hello", "edge", "voice1")
    key2 = generate_cache_key("hello", "edge", "voice1")
    key3 = generate_cache_key("hello", "edge", "voice2")
    
    assert key1 == key2  # Same inputs = same key
    assert key1 != key3  # Different inputs = different key
    assert len(key1) == 64  # SHA256 hash length


def test_sanitize_filename():
    """Test filename sanitization."""
    assert sanitize_filename("hello.txt") == "hello.txt"
    assert sanitize_filename("hello/world.txt") == "hello_world.txt"
    assert sanitize_filename("hello:world.txt") == "hello_world.txt"
    assert sanitize_filename("<test>.txt") == "_test_.txt"


def test_format_file_size():
    """Test file size formatting."""
    assert format_file_size(100) == "100.0 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1024 * 1024) == "1.0 MB"
    assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"


def test_is_valid_language_code():
    """Test language code validation."""
    assert is_valid_language_code("en-US") is True
    assert is_valid_language_code("zh-CN") is True
    assert is_valid_language_code("en") is False
    assert is_valid_language_code("en-us") is False
    assert is_valid_language_code("invalid") is False


def test_truncate_text():
    """Test text truncation."""
    text = "This is a long text that needs to be truncated"
    
    # Result should be exactly max_length characters
    assert truncate_text(text, 20) == "This is a long te..."  # 20 chars
    assert truncate_text(text, 100) == text
    assert truncate_text(text, 20, ">>") == "This is a long tex>>"  # 20 chars


def test_calculate_duration_from_text():
    """Test duration calculation."""
    text = "This is a test sentence with ten words in it."
    
    duration = calculate_duration_from_text(text)
    assert duration > 0
    
    # Faster rate should have shorter duration
    duration_fast = calculate_duration_from_text(text, rate=2.0)
    assert duration_fast < duration


def test_parse_voice_id():
    """Test voice ID parsing."""
    result1 = parse_voice_id("en-US-JennyNeural")
    assert result1["language"] == "en-US"
    assert result1["name"] == "JennyNeural"
    assert result1["locale"] == "en"
    assert result1["region"] == "US"
    
    result2 = parse_voice_id("en-Jenny")
    assert result2["language"] == "en"
    assert result2["name"] == "Jenny"
    
    result3 = parse_voice_id("SimpleVoice")
    assert result3["name"] == "SimpleVoice"
