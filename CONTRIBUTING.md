# Contributing to TTS System

Thank you for your interest in contributing to TTS System! This document provides guidelines for contributions.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/tts_sys.git
   cd tts_sys
   ```

2. **Install Dependencies**
   ```bash
   uv sync --all-extras
   ```

3. **Create Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Code Style

We use the following tools for code quality:

- **Black**: Code formatting
- **Ruff**: Linting
- **Mypy**: Type checking

Run before committing:
```bash
make format
make lint
make type-check
```

## Testing

All new features should include tests:

```bash
# Run all tests
make test

# Run with coverage
make test-cov
```

Test files should be placed in `tests/` directory with naming convention `test_*.py`.

## Adding New TTS Engines

1. **Create Engine Class**
   
   Create a new file in `packages/engines/`:
   ```python
   from packages.core.engine_base import TTSEngineBase
   from packages.shared.models import TTSRequest, Voice
   
   class MyCustomTTS(TTSEngineBase):
       @property
       def engine_name(self) -> str:
           return "custom"
       
       async def synthesize(self, request: TTSRequest) -> bytes:
           # Implement synthesis
           pass
       
       async def get_voices(self, language: str | None = None) -> list[Voice]:
           # Return available voices
           pass
   ```

2. **Register Engine**
   
   In `packages/api/main.py`:
   ```python
   from packages.engines.my_custom_tts import MyCustomTTS
   
   # In lifespan startup:
   engine_manager.register_engine_class(TTSEngine.CUSTOM, MyCustomTTS)
   ```

3. **Add Tests**
   
   Create `tests/test_engines/test_custom.py`:
   ```python
   @pytest.mark.asyncio
   async def test_custom_synthesize():
       engine = MyCustomTTS()
       # Test implementation
   ```

4. **Update Documentation**
   - Add engine to README.md
   - Update API.md with new engine details
   - Add configuration examples

## Pull Request Process

1. **Update Documentation**
   - Add/update docstrings
   - Update README if needed
   - Add changelog entry

2. **Ensure Tests Pass**
   ```bash
   make test
   make lint
   ```

3. **Commit Guidelines**
   - Use clear, descriptive commit messages
   - Reference issues if applicable
   - Keep commits focused and atomic

4. **Submit PR**
   - Provide clear description
   - Link related issues
   - Include screenshots if UI changes

## Code Review

- All submissions require review
- Address feedback promptly
- Be respectful and constructive

## Reporting Issues

When reporting issues, include:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant logs

## Feature Requests

Feature requests are welcome! Please:
- Search existing issues first
- Provide use case and rationale
- Be open to discussion

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for any questions or discussions.

Thank you for contributing to TTS System! 🎉
