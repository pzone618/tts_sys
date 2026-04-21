# 开发指南 (Development Guide)

本文档为 TTS System 的开发者提供详细的开发指南。

## 🛠️ 开发环境设置

### 前置要求

- **Python 3.13+**
- **uv** 包管理器
- **Git**
- **Visual Studio Code** (推荐) 或其他IDE

### 初始设置

```bash
# 1. 克隆仓库
git clone https://github.com/pzone618/tts_sys.git
cd tts_sys

# 2. 安装 uv（如果未安装）
# Windows
irm https://astral.sh/uv/install.ps1 | iex

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 创建开发环境
uv sync --all-extras

# 4. 配置环境变量
cp .env.example .env
# 根据需要编辑 .env

# 5. 初始化数据库
uv run alembic upgrade head

# 6. 运行开发服务器
make run
```

---

## 📁 项目结构详解

```
tts_sys/
├── packages/                 # 主代码包
│   ├── shared/              # 共享模块
│   │   ├── enums.py        # 枚举定义
│   │   ├── models.py       # Pydantic 数据模型
│   │   └── utils.py        # 工具函数
│   ├── core/               # 核心业务逻辑
│   │   ├── engine_base.py     # 引擎抽象基类
│   │   ├── engine_manager.py  # 引擎管理器（单例）
│   │   ├── audio_processor.py # 音频处理
│   │   ├── cache_manager.py   # 缓存管理
│   │   └── circuit_breaker.py # 熔断器
│   ├── engines/            # TTS 引擎实现
│   │   ├── edge_tts_engine.py    # Edge TTS
│   │   ├── openai_tts_engine.py  # OpenAI TTS
│   │   ├── youdao_tts_engine.py  # Youdao TTS
│   │   └── pyttsx3_engine.py     # Pyttsx3 (离线)
│   └── api/                # FastAPI 应用
│       ├── main.py            # 应用入口
│       ├── config.py          # 配置管理
│       ├── database.py        # 数据库设置
│       └── routes/            # API 路由
│           ├── tts.py            # TTS 生成
│           ├── voices.py         # 声音列表
│           └── history.py        # 历史记录
├── tests/                   # 测试套件
│   ├── conftest.py         # pytest 配置
│   ├── test_engines.py     # 引擎测试
│   ├── test_api.py         # API 测试
│   └── ...
├── migrations/              # 数据库迁移
├── docs/                    # 文档
├── examples/                # 示例代码
├── scripts/                 # 工具脚本
├── storage/                 # 存储目录
│   ├── cache/              # 音频缓存
│   └── temp/               # 临时文件
└── database/                # SQLite 数据库

```

---

## 🔧 开发工作流

### 1. 创建新分支

```bash
# 从 main 分支创建新分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. 开发新功能

```bash
# 启动开发服务器（自动重载）
make run

# 或手动启动
uv run uvicorn packages.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 代码质量检查

```bash
# 格式化代码 (Black)
make format
# 或
uv run black packages/ tests/

# Lint 检查 (Ruff)
make lint
# 或
uv run ruff check packages/ tests/

# 自动修复
uv run ruff check --fix packages/ tests/

# 类型检查 (Mypy)
make type-check
# 或
uv run mypy packages/
```

### 4. 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试文件
uv run pytest tests/test_engines.py -v

# 运行特定测试函数
uv run pytest tests/test_engines.py::test_edge_tts_synthesize -v

# 生成覆盖率报告
make test-cov
# 查看 htmlcov/index.html

# 快速测试（跳过慢速测试）
uv run pytest tests/ -m "not slow"

# 并行运行
uv run pytest tests/ -n auto
```

### 5. 提交代码

```bash
# 暂存更改
git add .

# 提交（遵循 Conventional Commits）
git commit -m "feat: add new TTS engine"

# 提交类型：
# feat: 新功能
# fix: 修复bug
# docs: 文档更新
# style: 代码格式（不影响功能）
# refactor: 重构
# test: 测试相关
# chore: 构建/工具相关

# 推送到远程
git push origin feature/your-feature-name
```

---

## 🎨 代码风格指南

### Python 代码风格

我们遵循 **PEP 8** 和 **Google Python Style Guide**：

```python
# ✅ 好的示例
from typing import Any

from loguru import logger
from packages.shared.models import TTSRequest, Voice


class MyTTSEngine:
    """TTS engine implementation.
    
    This class implements the TTS engine interface
    for the custom service.
    """
    
    def __init__(self, api_key: str) -> None:
        """Initialize engine.
        
        Args:
            api_key: API key for authentication
        """
        self.api_key = api_key
        self._is_initialized = False
    
    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech from text.
        
        Args:
            request: TTS request with text and voice settings
            
        Returns:
            Audio data as bytes
            
        Raises:
            ValueError: If request is invalid
            RuntimeError: If synthesis fails
        """
        if not request.text:
            raise ValueError("Text cannot be empty")
        
        try:
            # Implementation here
            audio_data = await self._call_api(request)
            logger.info(f"Synthesized {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise RuntimeError("Synthesis failed") from e


# ❌ 不好的示例
class myengine:  # 类名应该用 PascalCase
    def synthesis(self,req):  # 缺少类型注解
        if not req.text:return None  # 应该换行
        result=self.call(req)  # 应该用空格
        return result  # 应该添加日志和错误处理
```

### 命名约定

- **类名**: `PascalCase` (如 `TTSEngine`)
- **函数/方法**: `snake_case` (如 `synthesize_speech`)
- **常量**: `UPPER_SNAKE_CASE` (如 `MAX_TEXT_LENGTH`)
- **私有成员**: `_leading_underscore` (如 `_api_key`)
- **类型变量**: `PascalCase` (如 `T`, `RequestType`)

### 类型注解

始终添加类型注解：

```python
from typing import Optional, List, Dict, Any

# 函数注解
async def get_voices(
    language: str | None = None
) -> list[Voice]:
    """Get available voices."""
    pass

# 变量注解
voices: list[Voice] = []
cache: dict[str, Any] = {}
```

---

## 🧪 测试指南

### 测试结构

```bash
tests/
├── conftest.py              # pytest fixtures
├── test_utils.py            # 工具函数测试
├── test_engines.py          # 引擎测试
├── test_api.py              # API 测试
├── test_cache_manager.py    # 缓存管理器测试
└── ...
```

### 编写测试

```python
import pytest
from packages.engines.edge_tts_engine import EdgeTTSEngine
from packages.shared.models import TTSRequest
from packages.shared.enums import TTSEngine, AudioFormat


class TestEdgeTTS:
    """Test Edge TTS engine."""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return EdgeTTSEngine()
    
    @pytest.fixture
    def sample_request(self):
        """Create sample request."""
        return TTSRequest(
            text="Hello, world!",
            engine=TTSEngine.EDGE,
            voice="en-US-JennyNeural",
            rate=1.0,
            volume=1.0,
            format=AudioFormat.MP3,
        )
    
    @pytest.mark.asyncio
    async def test_synthesize_success(self, engine, sample_request):
        """Test successful synthesis."""
        # Act
        audio_data = await engine.synthesize(sample_request)
        
        # Assert
        assert isinstance(audio_data, bytes)
        assert len(audio_data) > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self, engine):
        """Test synthesis with empty text."""
        # Arrange
        request = TTSRequest(
            text="",
            engine=TTSEngine.EDGE,
            voice="en-US-JennyNeural",
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await engine.synthesize(request)
```

### Mock 外部API

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_openai_synthesize_with_mock():
    """Test OpenAI synthesis with mocked API."""
    engine = OpenAITTSEngine(api_key="test-key")
    request = TTSRequest(
        text="Test",
        engine=TTSEngine.OPENAI,
        voice="nova",
    )
    
    # Mock httpx client
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        mock_client.return_value.post.return_value = mock_response
        
        audio_data = await engine.synthesize(request)
        
        assert audio_data == b"fake_audio_data"
```

### 测试覆盖率

- **目标覆盖率**: 80%+
- **关键模块**: 90%+ (engine_manager, circuit_breaker, cache_manager)

```bash
# 生成覆盖率报告
uv run pytest --cov=packages --cov-report=html --cov-report=term

# 查看详细报告
open htmlcov/index.html
```

---

## 🔌 添加新的 TTS 引擎

### 步骤 1: 创建引擎类

在 `packages/engines/` 创建新文件 `my_custom_engine.py`:

```python
"""My Custom TTS Engine implementation."""

from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import AudioFormat, TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice


class MyCustomTTSEngine(TTSEngineBase):
    """Custom TTS engine."""
    
    def __init__(self, api_key: str) -> None:
        """Initialize engine.
        
        Args:
            api_key: API key for authentication
        """
        super().__init__()
        self.api_key = api_key
        self._voices_cache: list[Voice] = []
    
    @property
    def engine_name(self) -> str:
        """Get engine name."""
        return TTSEngine.CUSTOM.value
    
    async def initialize(self) -> None:
        """Initialize engine and load resources."""
        await self._load_voices()
        logger.info("Custom TTS engine initialized")
    
    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech.
        
        Args:
            request: TTS request
            
        Returns:
            Audio data
        """
        logger.info(f"Synthesizing with Custom TTS: {len(request.text)} chars")
        
        # TODO: Implement API call
        audio_data = await self._call_api(request)
        
        return audio_data
    
    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices."""
        if not self._voices_cache:
            await self._load_voices()
        
        if language:
            return [v for v in self._voices_cache if v.language == language]
        
        return self._voices_cache
    
    async def health_check(self) -> bool:
        """Check engine health."""
        try:
            voices = await self.get_voices()
            return len(voices) > 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _load_voices(self) -> None:
        """Load voices from API."""
        # TODO: Implement voice loading
        pass
    
    async def _call_api(self, request: TTSRequest) -> bytes:
        """Call TTS API."""
        # TODO: Implement API call
        pass
```

### 步骤 2: 添加枚举

在 `packages/shared/enums.py` 添加引擎枚举：

```python
class TTSEngine(str, Enum):
    """TTS engine types."""
    EDGE = "edge"
    OPENAI = "openai"
    YOUDAO = "youdao"
    PYTTSX3 = "pyttsx3"
    CUSTOM = "custom"  # ← 添加这行
```

### 步骤 3: 注册引擎

在 `packages/api/main.py` 注册引擎：

```python
from packages.engines.my_custom_engine import MyCustomTTSEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # ... 其他引擎注册 ...
    
    # 注册自定义引擎
    if settings.CUSTOM_TTS_ENABLED:
        engine_manager.register_engine_class(
            TTSEngine.CUSTOM,
            MyCustomTTSEngine
        )
        await engine_manager.initialize_engine(
            TTSEngine.CUSTOM,
            api_key=settings.CUSTOM_API_KEY
        )
    
    yield
```

### 步骤 4: 添加配置

在 `.env.example` 添加配置:

```bash
# My Custom TTS
CUSTOM_TTS_ENABLED=false
CUSTOM_API_KEY=
```

在 `packages/api/config.py` 添加设置：

```python
class Settings(BaseSettings):
    # ... 其他设置 ...
    
    # My Custom TTS
    CUSTOM_TTS_ENABLED: bool = False
    CUSTOM_API_KEY: str = ""
```

### 步骤 5: 添加测试

创建 `tests/test_custom_engine.py`:

```python
import pytest
from packages.engines.my_custom_engine import MyCustomTTSEngine


class TestCustomEngine:
    """Test Custom TTS engine."""
    
    @pytest.fixture
    def engine(self):
        return MyCustomTTSEngine(api_key="test-key")
    
    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        await engine.initialize()
        assert engine._voices_cache is not None
    
    # ... 更多测试 ...
```

### 步骤 6: 更新文档

- 在 `README.md` 的功能列表中添加引擎
- 在 `docs/API.md` 中添加使用示例
- 更新 `CHANGELOG.md`

---

## 📊 调试技巧

### 使用日志记录

```python
from loguru import logger

# 不同级别的日志
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with traceback")

# 上下文日志
with logger.contextualize(request_id=req_id):
    logger.info("Processing request")
```

### 使用 IPython/Jupyter

```bash
# 安装 ipython
uv pip install ipython

# 启动交互式 shell
uv run ipython

# 在代码中设置断点
import IPython; IPython.embed()
```

### 使用 VS Code 调试器

创建 `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "packages.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v"
      ]
    }
  ]
}
```

---

## 🚀 发布流程

### 1. 版本控制

我们遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- `MAJOR.MINOR.PATCH`
- `0.1.0` → `0.2.0` (新功能)
- `0.2.0` → `0.2.1` (修复bug)
- `0.2.1` → `1.0.0` (重大更改)

### 2. 发布清单

- [ ] 所有测试通过 (`make test`)
- [ ] 代码覆盖率 ≥ 80%
- [ ] 代码格式化 (`make format`)
- [ ] Lint检查通过 (`make lint`)
- [ ] 类型检查通过 (`make type-check`)
- [ ] 更新 `CHANGELOG.md`
- [ ] 更新版本号 (`pyproject.toml`)
- [ ] 创建 Git tag
- [ ] 构建 Docker 镜像

### 3. 发布命令

```bash
# 更新版本号
# 编辑 pyproject.toml

# 提交更改
git add .
git commit -m "chore: release v0.2.0"

# 创建 tag
git tag -a v0.2.0 -m "Release v0.2.0"

# 推送
git push origin main --tags

# 构建 Docker 镜像
docker build -t tts-system:0.2.0 .
docker tag tts-system:0.2.0 tts-system:latest
```

---

## 📚 相关资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [pytest 文档](https://docs.pytest.org/)
- [uv 文档](https://github.com/astral-sh/uv)

---

## 💬 开发者社区

- **Issues**: [GitHub Issues](https://github.com/pzone618/tts_sys/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pzone618/tts_sys/discussions)
- **Contributing**: 查看 [CONTRIBUTING.md](../CONTRIBUTING.md)

---

Happy Coding! 🎉
