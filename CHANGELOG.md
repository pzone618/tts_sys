# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - High Availability & Fault Tolerance

### Added

#### 🛡️ Circuit Breaker Pattern
- **Circuit Breaker Implementation** (`packages/core/circuit_breaker.py`)
  - Automatic failure detection with configurable thresholds
  - Three states: CLOSED (normal), OPEN (blocked), HALF_OPEN (testing recovery)
  - Per-engine circuit tracking and statistics
  - Automatic recovery with gradual testing
  - Global circuit breaker instance

#### 🔄 Automatic Fallback System
- **Enhanced Engine Manager** with fallback capabilities:
  - `synthesize_with_fallback()` method for automatic degradation
  - Configurable fallback chains (default or custom)
  - Engine categorization: online (network-dependent) vs. offline (local)
  - Intelligent voice mapping across different engines
  - Retry mechanism with configurable attempts per engine
  - `get_fallback_chain()` for fallback strategy generation

#### 🔌 Offline TTS Engine
- **Pyttsx3 Engine** (`packages/engines/pyttsx3_engine.py`)
  - Fully offline text-to-speech using system voices
  - Platform support: Windows (SAPI5), macOS (NSSpeechSynthesizer), Linux (espeak)
  - Acts as ultimate fallback when all online services fail
  - Zero network dependency, guaranteed availability
  - Configurable rate and volume parameters

#### 📊 API Enhancements
- **New Request Parameters** in `TTSRequest`:
  - `fallback_engines: list[TTSEngine] | None` - Custom fallback chain
  - `enable_auto_fallback: bool` - Toggle automatic fallback (default: true)
  - `max_retries: int` - Retry attempts per engine (default: 2, range: 0-5)
  
- **New API Endpoints**:
  - `GET /api/v1/tts/circuit-breaker/status` - Monitor circuit breaker states for all engines
  - `POST /api/v1/tts/circuit-breaker/reset/{engine}` - Manually reset a specific circuit
  
- **Enhanced Response Metadata**:
  - `requested_engine` - Originally requested engine
  - `actual_engine` - Engine that actually processed the request
  - `fallback_occurred` - Boolean flag indicating if fallback was used

#### 📖 Documentation
- **[Fallback Strategy Guide](docs/FALLBACK_STRATEGY.md)**: Complete 60KB guide including:
  - 5 implementation approaches with full code examples
  - Circuit breaker pattern explanation with state diagrams
  - Configuration options and environment variables
  - API usage examples with fallback scenarios
  - Fallback chain strategies and decision trees
  - Monitoring and observability guide
  
- **Updated [README.md](README.md)**:
  - High availability features in Features section
  - Fallback API usage examples
  - Circuit breaker monitoring examples
  - Link to fallback strategy documentation

#### 🧪 Testing & Examples
- **Comprehensive Test Suite** (`tests/test_fallback.py`):
  - Circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
  - Fallback chain generation (default and custom)
  - Synthesis with fallback (success and failure scenarios)
  - Engine categorization validation
  - 20+ test cases covering all edge cases
  
- **Interactive Demo Script** (`examples/fallback_demo.py`):
  - 7 real-world scenarios demonstrating fallback
  - Circuit breaker monitoring example
  - Stress testing with concurrent requests
  - Quality control with automatic fallback

#### ⚙️ Configuration
- **New Environment Variables** (see `.env.example`):
  - `PYTTSX3_ENABLED=true` - Enable offline fallback engine
  - `TTS_ENABLE_AUTO_FALLBACK=true` - Global fallback toggle
  - `TTS_MAX_RETRIES=2` - Default retry count per engine
  - `CIRCUIT_BREAKER_FAILURE_THRESHOLD=5` - Failures before opening circuit
  - `CIRCUIT_BREAKER_TIMEOUT_SECONDS=60` - Wait time before testing recovery
  - `CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2` - Successes needed to close circuit

#### 📦 Dependencies
- Added `pyttsx3>=2.90` for offline TTS support (Windows: pywin32, Linux: espeak)

### Changed

- **Engine Manager** (`packages/core/engine_manager.py`):
  - Refactored to support online/offline engine categorization
  - Added fallback chain generation logic
  - Integrated circuit breaker for all engine calls
  - Enhanced voice mapping with multi-strategy fallback
  
- **API Routes** (`packages/api/routes/tts.py`):
  - `generate_speech()` now uses `synthesize_with_fallback()`
  - Removed explicit engine availability check (handled by fallback system)
  - Enhanced response with fallback metadata for transparency
  - Database records now store actual engine used (not just requested)
  
- **Application Startup** (`packages/api/main.py`):
  - Register and initialize pyttsx3 engine on startup
  - Graceful handling of pyttsx3 initialization failures (logs warning if unavailable)
  - Import pyttsx3 engine class

- **Shared Models** (`packages/shared/models.py`):
  - Enhanced `TTSRequest` with fallback configuration fields
  - Backward compatible - all new fields are optional

- **Shared Enums** (`packages/shared/enums.py`):
  - Added `TTSEngine.PYTTSX3` enum value

### Fixed

- Improved error handling in engine synthesis with detailed logging
- Better exception messages for fallback failures
- Consistent voice mapping across different engines
- Circuit breaker state transitions now thread-safe

### Security

- Circuit breaker prevents cascading failures and DOS scenarios
- Offline fallback ensures service availability even during network attacks

---

## [0.1.0] - 2026-04-21

### Added
- Initial release of TTS System
- Monorepo architecture with packages (shared, core, engines, api)
- Support for multiple TTS engines:
  - Edge TTS (Microsoft) - Free, no API key required
  - Youdao TTS - Chinese TTS with emotional voices
  - OpenAI TTS - High-quality multilingual voices
- FastAPI-based REST API with async support
- Audio caching system with configurable TTL
- SQLite database with Alembic migrations
- Request history and usage statistics
- Voice listing and filtering
- Comprehensive test suite
- Docker and docker-compose support
- Complete API documentation
- Deployment guides for various platforms
- Health check endpoints
- CORS middleware
- Error handling and validation
- Type hints throughout codebase
- uv package manager support
- Quick start script

### Features
- **Text-to-Speech Generation**: Convert text to audio using multiple engines
- **Voice Management**: List, search, and filter available voices
- **Caching**: Intelligent caching to reduce API calls and improve performance
- **History**: Track all TTS requests with detailed metadata
- **Statistics**: Usage analytics and performance metrics
- **Multi-Engine**: Easy integration of new TTS engines via plugin architecture
- **Audio Parameters**: Control rate, volume, pitch, and format
- **Async Processing**: Full async/await support for high concurrency

### Documentation
- README with quick start guide
- API documentation with examples
- Deployment guide for various platforms
- Contributing guidelines
- Code of conduct
- Comprehensive inline documentation

### Configuration
- Environment-based configuration
- Support for multiple deployment scenarios
- Configurable caching and storage
- Rate limiting support

### Developer Experience
- Simple project structure
- Type-safe code with Pydantic
- Comprehensive test coverage
- Code quality tools (black, ruff, mypy)
- Development scripts and Makefile
- Hot reload in development mode

[0.1.0]: https://github.com/yourusername/tts_sys/releases/tag/v0.1.0
