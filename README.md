# TTS System - Enterprise Text-to-Speech API

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready, extensible Text-to-Speech API system with support for multiple TTS engines.

## 🚀 Features

- **Multi-Engine Support**: Edge TTS, Youdao TTS, Azure TTS, Google TTS, OpenAI TTS, Pyttsx3 (offline)
- **High Availability**: Automatic fallback to offline engines when online services fail
- **Circuit Breaker**: Intelligent failure detection and automatic recovery
- **Audio Quality Control**: Configurable quality presets (standard/high/hd) and advanced audio parameters (bitrate, sample rate)
- **Async Processing**: Full async/await support for high performance
- **Audio Caching**: Smart caching to reduce API calls and improve response time
- **Request History**: Track all TTS requests with SQLite database
- **RESTful API**: Clean, well-documented FastAPI endpoints
- **Extensible Architecture**: Plugin-based engine system for easy integration
- **Type Safety**: Full type hints with Pydantic models
- **Database Migration**: Alembic for version-controlled schema changes
- **Monorepo Structure**: Clean code organization with package separation

## 📁 Project Structure

```
tts_sys/
├── packages/
│   ├── shared/          # Shared types, models, and utilities
│   │   ├── __init__.py
│   │   ├── models.py    # Pydantic models
│   │   ├── enums.py     # Enums and constants
│   │   └── utils.py     # Helper functions
│   ├── core/            # Core business logic
│   │   ├── __init__.py
│   │   ├── engine_base.py    # TTS Engine abstract base
│   │   ├── engine_manager.py # Engine registry and factory
│   │   ├── audio_processor.py # Audio file handling
│   │   └── cache_manager.py   # Caching logic
│   ├── engines/         # TTS engine implementations
│   │   ├── __init__.py
│   │   ├── edge_tts.py       # Microsoft Edge TTS
│   │   ├── youdao_tts.py     # Youdao TTS
│   │   ├── azure_tts.py      # Azure Cognitive Services
│   │   ├── google_tts.py     # Google Cloud TTS
│   │   └── openai_tts.py     # OpenAI TTS
│   └── api/             # FastAPI application
│       ├── __init__.py
│       ├── main.py      # App entry point
│       ├── routes/      # API routes
│       │   ├── __init__.py
│       │   ├── tts.py
│       │   ├── voices.py
│       │   └── history.py
│       ├── database.py  # Database setup
│       └── config.py    # Configuration
├── migrations/          # Alembic migrations
│   ├── versions/
│   └── env.py
├── storage/             # Audio file storage
│   └── cache/
├── tests/               # Test suite
│   ├── test_engines/
│   ├── test_api/
│   └── conftest.py
├── pyproject.toml       # uv configuration
├── alembic.ini          # Alembic config
├── .env.example         # Environment template
├── .gitignore
└── README.md
```

## 🛠️ Tech Stack

- **Language**: Python 3.13
- **Package Manager**: uv
- **Web Framework**: FastAPI
- **Database**: SQLite + SQLAlchemy 2.0
- **Migration**: Alembic
- **TTS Engines**: edge-tts, custom implementations
- **Testing**: pytest + pytest-asyncio
- **Code Quality**: ruff, black, mypy

## 🚦 Quick Start

### Prerequisites

- Python 3.13+
- uv package manager

### Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <your-repo-url>
cd tts_sys

# Create virtual environment and install dependencies
uv sync

# Initialize database
uv run alembic upgrade head

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Running the Server

```bash
# Development mode with auto-reload (uses API_PORT from .env, default: 8000)
make run

# Or manually with uvicorn
uv run uvicorn packages.api.main:app --reload --host 0.0.0.0 --port ${API_PORT:-8000}

# Production mode
make prod
```

Visit `http://localhost:<API_PORT>/docs` for interactive API documentation (default port: 8000).

**Note**: The port is configurable via `API_PORT` in your `.env` file.

## 📚 API Endpoints

### TTS Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tts/generate` | Generate speech from text |
| GET | `/api/v1/tts/cache/stats` | Get cache statistics |
| DELETE | `/api/v1/tts/cache/clear` | Clear all cached audio |
| POST | `/api/v1/tts/cache/cleanup` | Clean up expired cache entries |

### Voice Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/voices` | List available voices (with filters) |
| GET | `/api/v1/voices/{voice_id}` | Get voice details |

### History & Statistics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/history` | Get request history (paginated) |
| GET | `/api/v1/history/stats` | Get usage statistics |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/audio/{filename}` | Download audio file |

📖 **Full API documentation**: http://localhost:<API_PORT>/api/v1/docs (default port: 8000)

**Note**: Replace `<API_PORT>` with your configured port from `.env` file.

## 💡 API Usage Examples

### Generate Speech

```bash
# Basic usage
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "edge",
    "voice": "en-US-JennyNeural",
    "rate": 1.0,
    "volume": 1.0
  }'

# With quality settings (recommended)
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "openai",
    "voice": "nova",
    "quality": "hd"
  }'

# With advanced audio settings
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "edge",
    "voice": "en-US-JennyNeural",
    "bitrate": 192,
    "sample_rate": 24000
  }'

# With automatic fallback (recommended for production)
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "openai",
    "voice": "nova",
    "enable_auto_fallback": true,
    "max_retries": 2
  }'

# With custom fallback chain
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，世界",
    "engine": "openai",
    "voice": "nova",
    "fallback_engines": ["youdao", "edge", "pyttsx3"]
  }'
```

**Response with fallback information:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "audio_url": "/api/v1/audio/abc123.mp3",
  "status": "completed",
  "metadata": {
    "requested_engine": "openai",
    "actual_engine": "edge",
    "fallback_occurred": true
  }
}
```

### List Available Voices

```bash
# All voices
curl "http://localhost:8000/api/v1/voices"

# Filter by engine and language
curl "http://localhost:8000/api/v1/voices?engine=edge&language=en-US"

# Search voices
curl "http://localhost:8000/api/v1/voices?search=jenny"
```

### Get Request History

```bash
# Recent requests
curl "http://localhost:8000/api/v1/history?limit=10"

# Filter by engine and date
curl "http://localhost:8000/api/v1/history?engine=edge&from_date=2026-04-01T00:00:00Z"
```

### Get Statistics

```bash
curl "http://localhost:8000/api/v1/history/stats"
```

### Cache Management

```bash
# Get cache stats
curl "http://localhost:8000/api/v1/tts/cache/stats"

# Clear cache
curl -X DELETE "http://localhost:8000/api/v1/tts/cache/clear"

# Cleanup expired entries
curl -X POST "http://localhost:8000/api/v1/tts/cache/cleanup"
```

### Circuit Breaker Monitoring

```bash
# Check circuit breaker status for all engines
curl "http://localhost:8000/api/v1/tts/circuit-breaker/status"

# Response:
# {
#   "circuit_breakers": {
#     "openai": {
#       "state": "open",
#       "failure_count": 5,
#       "success_count": 0,
#       "last_failure": 1234567890.0
#     },
#     "edge": {
#       "state": "closed",
#       "failure_count": 0,
#       "success_count": 10,
#       "last_success": 1234567895.0
#     }
#   },
#   "available_engines": ["edge", "pyttsx3"]
# }

# Manually reset circuit breaker for an engine
curl -X POST "http://localhost:8000/api/v1/tts/circuit-breaker/reset/openai"
```

## 🔌 Adding New TTS Engines

**This system is highly extensible!** Adding a new TTS engine is simple and requires no changes to core code.

### Quick Overview

1. ✅ Create engine class inheriting from `TTSEngineBase`
2. ✅ Implement 3 required methods: `engine_name`, `synthesize`, `get_voices`
3. ✅ Register engine in `main.py`
4. ✅ Add configuration in `.env`

**That's it!** No need to modify API routes, database models, or caching logic.

### Example: Basic Engine Structure

```python
from packages.core.engine_base import TTSEngineBase
from packages.shared.models import TTSRequest, Voice

class MyCustomTTS(TTSEngineBase):
    @property
    def engine_name(self) -> str:
        return "mycustom"
    
    async def synthesize(self, request: TTSRequest) -> bytes:
        # Your TTS implementation here
        return audio_bytes
    
    async def get_voices(self, language: str | None = None) -> list[Voice]:
        # Return available voices
        return voices_list
```

**📖 Complete Guide**: See [docs/ADDING_NEW_ENGINE.md](docs/ADDING_NEW_ENGINE.md) for a detailed step-by-step tutorial with a full ElevenLabs TTS example.

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=packages --cov-report=html

# Run specific test file
uv run pytest tests/test_engines/test_edge_tts.py
```

## 📝 Configuration

Configure via environment variables or `.env` file:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000  # Change this to use a different port
API_DEBUG=false

# Database
DATABASE_URL=sqlite:///./database/tts_sys.db

# Storage
STORAGE_PATH=./storage
CACHE_ENABLED=true
CACHE_MAX_SIZE_MB=1024

# TTS Engine Keys
YOUDAO_APP_KEY=your_app_key
YOUDAO_APP_SECRET=your_app_secret
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
OPENAI_API_KEY=your_openai_key
```

## 📊 Database Schema

- **tts_requests**: TTS request history and metadata
- **audio_cache**: Cached audio files with hash-based lookup
- **engine_config**: Per-engine configuration and credentials
- **usage_stats**: API usage statistics and metrics

## � Testing

The project maintains comprehensive test coverage across all core components.

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
uv run pytest --cov=packages --cov-report=html --cov-report=term

# Run specific test file
uv run pytest tests/test_engines.py

# Run tests with verbose output
uv run pytest -v

# Run tests in parallel
uv run pytest -n auto
```

### Test Coverage

**Current Coverage: 75%** (112 test cases)

| Module | Coverage | Test Cases |
|--------|----------|------------|
| `packages/shared/utils.py` | 100% | 7 |
| `packages/core/cache_manager.py` | 90% | 14 |
| `packages/core/circuit_breaker.py` | 90% | 21 |
| `packages/core/audio_processor.py` | 85% | 12 |
| `packages/core/engine_manager.py` | 85% | 18 |
| `packages/api/routes/` | 80% | 35 |
| `packages/engines/edge_tts.py` | 85% | 5 |

**Test Organization:**
- `tests/test_utils.py` - Utility functions
- `tests/test_engines.py` - TTS engine implementations
- `tests/test_api.py` - Basic API endpoints
- `tests/test_api_advanced.py` - Advanced features (quality, fallback, caching)
- `tests/test_audio_processor.py` - Audio file handling
- `tests/test_cache_manager.py` - Caching system
- `tests/test_engine_manager.py` - Engine management
- `tests/test_fallback.py` - Circuit breaker and fallback logic

📖 **Detailed Coverage Report**: [TEST_COVERAGE.md](docs/TEST_COVERAGE.md)

### Testing Best Practices

- Mock external API calls using `pytest-mock` or `unittest.mock`
- Use `pytest-asyncio` for async test functions
- Isolate tests with fixtures defined in `conftest.py`
- Clean up test artifacts in teardown
- Measure coverage and maintain 80%+ target

## �🤝 Contributing

Contributions are welcome! Please read our contributing guidelines.

## � Documentation

- **[API Documentation](docs/API.md)** - 完整的API使用指南（中文）
- **[Architecture Guide](docs/ARCHITECTURE.md)** - 系统架构和设计模式详解- **[Fallback Strategy](docs/FALLBACK_STRATEGY.md)** - 降级容错方案和熔断器实现- **[Adding New Engines](docs/ADDING_NEW_ENGINE.md)** - 新引擎开发教程（含完整示例）
- **[Deployment Guide](docs/DEPLOYMENT.md)** - 多平台部署指南
- **[Quick Start](QUICKSTART.md)** - 5分钟快速上手

## �📄 License

MIT License - see LICENSE file for details

## 🔗 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Edge TTS](https://github.com/rany2/edge-tts)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [uv Documentation](https://github.com/astral-sh/uv)
