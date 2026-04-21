"""Test configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.api.database import Base
from packages.api.main import app
from packages.core.circuit_breaker import circuit_breaker, CircuitState
from packages.core.engine_manager import engine_manager


@pytest.fixture(scope="session")
def test_db():
    """Create a test database for the session."""
    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    db_url = f"sqlite:///{db_path}"
    
    # Create engine and tables
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestSessionLocal
    
    # Cleanup
    engine.dispose()
    if db_path.exists():
        db_path.unlink()
    os.rmdir(temp_dir)


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset all circuit breakers before each test."""
    # Reset all circuit breaker stats
    circuit_breaker.stats.clear()
    
    yield


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


@pytest.fixture
def sample_tts_request():
    """Sample TTS request for testing."""
    return {
        "text": "Hello, this is a test.",
        "engine": "edge",
        "voice": "en-US-JennyNeural",
        "rate": 1.0,
        "volume": 1.0,
        "pitch": 1.0,
        "format": "mp3",
        "use_cache": True,
    }

