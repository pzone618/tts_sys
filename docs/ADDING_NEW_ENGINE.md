# 添加新 TTS 引擎指南

本文档说明如何向 TTS 系统添加新的 TTS 引擎。系统采用**插件式架构**，添加新引擎非常简单。

## 🎯 可扩展性特性

✅ **插件式架构** - 基于抽象基类，所有引擎遵循统一接口  
✅ **自动注册** - 通过 EngineManager 自动管理引擎生命周期  
✅ **配置驱动** - 通过 `.env` 文件即可启用/禁用引擎  
✅ **零侵入** - 添加新引擎无需修改核心代码  
✅ **类型安全** - 完整的类型提示和 Pydantic 验证  

## 📋 添加新引擎的步骤

### 步骤 1: 在 `enums.py` 添加引擎类型

**文件**: `packages/shared/enums.py`

```python
class TTSEngine(str, Enum):
    """Available TTS engines."""

    EDGE = "edge"
    YOUDAO = "youdao"
    AZURE = "azure"
    GOOGLE = "google"
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"  # 👈 新增
```

### 步骤 2: 创建引擎实现

**文件**: `packages/engines/elevenlabs_tts_engine.py`

```python
"""ElevenLabs TTS engine implementation."""

import httpx
from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice


class ElevenLabsTTSEngine(TTSEngineBase):
    """ElevenLabs TTS engine implementation.
    
    Requires ElevenLabs API key.
    Documentation: https://docs.elevenlabs.io/api-reference/text-to-speech
    """

    API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize ElevenLabs TTS engine.
        
        Args:
            config: Must include 'api_key'
        """
        super().__init__(config)
        self.api_key = self.get_config("api_key")

        if not self.api_key:
            logger.warning("ElevenLabs TTS: Missing api_key")
            self.disable()

    @property
    def engine_name(self) -> str:
        """Return engine name."""
        return TTSEngine.ELEVENLABS.value

    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech using ElevenLabs TTS.
        
        Args:
            request: TTS request
        
        Returns:
            Audio data in MP3 format
        """
        if not self.is_enabled():
            raise RuntimeError("ElevenLabs TTS engine is not enabled (missing API key)")

        try:
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            }

            # Map quality to model_id
            model_id = self._select_model(request)

            payload = {
                "text": request.text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "speed": request.rate,
                },
            }

            url = f"{self.API_URL}/{request.voice}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()

            audio_data = response.content
            quality_info = f"quality={request.quality}" if request.quality else "default"
            logger.info(
                f"ElevenLabs TTS synthesis completed: {len(audio_data)} bytes, "
                f"voice={request.voice}, model={model_id}, {quality_info}"
            )
            return audio_data

        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs TTS HTTP error: {e}")
            raise RuntimeError(f"ElevenLabs TTS request failed: {e}") from e
        except Exception as e:
            logger.error(f"ElevenLabs TTS synthesis failed: {e}")
            raise RuntimeError(f"ElevenLabs TTS synthesis failed: {e}") from e

    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices from ElevenLabs.
        
        Args:
            language: Not used (ElevenLabs voices support multiple languages)
        
        Returns:
            List of available voices
        """
        if not self.is_enabled():
            return []

        try:
            headers = {"xi-api-key": self.api_key}
            url = "https://api.elevenlabs.io/v1/voices"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

            data = response.json()
            voices = []

            for v in data.get("voices", []):
                voice = Voice(
                    id=v["voice_id"],
                    name=v["name"],
                    language="multi",  # ElevenLabs voices are multilingual
                    gender=self._infer_gender(v),
                    engine=TTSEngine.ELEVENLABS,
                    description=v.get("description", ""),
                    tags=v.get("labels", {}).get("accent", []),
                )
                voices.append(voice)

            logger.info(f"Loaded {len(voices)} voices from ElevenLabs")
            return voices

        except Exception as e:
            logger.error(f"Failed to get ElevenLabs voices: {e}")
            return []

    def _select_model(self, request: TTSRequest) -> str:
        """Select model based on quality settings.
        
        Args:
            request: TTS request with quality settings
            
        Returns:
            Model ID
        """
        if request.quality and request.quality.value == "hd":
            return "eleven_multilingual_v2"  # HD model
        return "eleven_monolingual_v1"  # Standard model

    def _infer_gender(self, voice_data: dict) -> VoiceGender:
        """Infer gender from voice data.
        
        Args:
            voice_data: Voice data from API
            
        Returns:
            Inferred gender
        """
        labels = voice_data.get("labels", {})
        gender_label = labels.get("gender", "").lower()
        
        if "male" in gender_label and "female" not in gender_label:
            return VoiceGender.MALE
        elif "female" in gender_label:
            return VoiceGender.FEMALE
        return VoiceGender.NEUTRAL
```

### 步骤 3: 在 `config.py` 添加配置

**文件**: `packages/api/config.py`

```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ... 现有配置 ...
    
    # ElevenLabs TTS
    elevenlabs_tts_enabled: bool = False
    elevenlabs_api_key: str = ""
    
    def get_engine_config(self, engine: str) -> dict[str, str]:
        """Get configuration for a specific engine."""
        configs = {
            # ... 现有引擎 ...
            "elevenlabs": {
                "api_key": self.elevenlabs_api_key,
            },
        }
        return configs.get(engine, {})
```

### 步骤 4: 在 `.env.example` 添加环境变量

**文件**: `.env.example`

```env
# ... 现有配置 ...

# ElevenLabs TTS
ELEVENLABS_TTS_ENABLED=false
ELEVENLABS_API_KEY=
```

### 步骤 5: 在 `main.py` 注册引擎

**文件**: `packages/api/main.py`

```python
from packages.engines.edge_tts_engine import EdgeTTSEngine
from packages.engines.openai_tts_engine import OpenAITTSEngine
from packages.engines.youdao_tts_engine import YoudaoTTSEngine
from packages.engines.elevenlabs_tts_engine import ElevenLabsTTSEngine  # 👈 新增

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # ... 现有代码 ...
    
    # Register engine classes
    engine_manager.register_engine_class(TTSEngine.EDGE, EdgeTTSEngine)
    engine_manager.register_engine_class(TTSEngine.YOUDAO, YoudaoTTSEngine)
    engine_manager.register_engine_class(TTSEngine.OPENAI, OpenAITTSEngine)
    engine_manager.register_engine_class(TTSEngine.ELEVENLABS, ElevenLabsTTSEngine)  # 👈 新增
    
    # Initialize enabled engines
    # ... 现有代码 ...
    
    if settings.is_engine_enabled("elevenlabs"):  # 👈 新增
        engine_manager.initialize_engine(
            TTSEngine.ELEVENLABS, settings.get_engine_config("elevenlabs")
        )
        logger.info("✓ ElevenLabs TTS enabled")
    
    # ... 其余代码 ...
```

### 步骤 6: 添加测试（可选但推荐）

**文件**: `tests/test_engines/test_elevenlabs_tts.py`

```python
"""Tests for ElevenLabs TTS engine."""

import pytest
from packages.engines.elevenlabs_tts_engine import ElevenLabsTTSEngine
from packages.shared.enums import TTSEngine
from packages.shared.models import TTSRequest


@pytest.fixture
def engine():
    """Create ElevenLabs TTS engine."""
    config = {"api_key": "test_key"}
    return ElevenLabsTTSEngine(config)


def test_engine_name(engine):
    """Test engine name."""
    assert engine.engine_name == TTSEngine.ELEVENLABS.value


@pytest.mark.asyncio
async def test_get_voices_no_key():
    """Test get voices without API key."""
    engine = ElevenLabsTTSEngine()
    voices = await engine.get_voices()
    assert len(voices) == 0


# ... 更多测试 ...
```

## 🎯 完成！就这么简单！

添加新引擎只需要：

1. ✅ 1 个枚举定义（`enums.py`）
2. ✅ 1 个引擎实现类（`engines/`目录）
3. ✅ 2-3 行配置代码（`config.py`）
4. ✅ 2-3 行环境变量（`.env.example`）
5. ✅ 2-3 行注册代码（`main.py`）

**无需修改**：
- ❌ API 路由（自动支持）
- ❌ 数据库模型（通用设计）
- ❌ 缓存系统（引擎无关）
- ❌ 核心业务逻辑（完全解耦）

## 📊 当前支持的引擎

| 引擎 | 状态 | 特性 |
|------|------|------|
| Edge TTS | ✅ 已实现 | 免费，100+声音，无需API Key |
| Youdao TTS | ✅ 已实现 | 中文专用，支持情感语音 |
| OpenAI TTS | ✅ 已实现 | 6种高质量声音，多语言 |
| Azure TTS | 🔄 代码已有 | 企业级，400+声音 |
| Google TTS | 🔄 代码已有 | 220+声音，WaveNet |
| ElevenLabs | 📝 上面示例 | 超逼真语音，克隆功能 |

## 🔧 引擎实现要点

### 必须实现的方法

```python
class MyTTSEngine(TTSEngineBase):
    @property
    def engine_name(self) -> str:
        """返回引擎名称（必须）"""
        pass
    
    async def synthesize(self, request: TTSRequest) -> bytes:
        """合成语音（必须）"""
        pass
    
    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """获取可用声音列表（必须）"""
        pass
```

### 可选的辅助方法

```python
    async def validate_voice(self, voice_id: str, language: str | None = None) -> bool:
        """验证声音ID（已在基类实现）"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查（已在基类实现）"""
        pass
```

### 配置管理

```python
    def __init__(self, config: dict[str, str] | None = None):
        super().__init__(config)
        self.api_key = self.get_config("api_key")  # 从配置读取
        
        if not self.api_key:
            self.disable()  # 缺少必要配置时禁用引擎
```

## 💡 最佳实践

### 1. 错误处理

```python
async def synthesize(self, request: TTSRequest) -> bytes:
    try:
        # 调用外部API
        response = await client.post(...)
        return response.content
    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        raise RuntimeError(f"Synthesis failed: {e}") from e
```

### 2. 日志记录

```python
logger.info(f"Synthesis completed: {len(audio_data)} bytes")
logger.error(f"Failed to load voices: {e}")
logger.warning("Missing API key, engine disabled")
```

### 3. 质量控制

```python
def _select_model(self, request: TTSRequest) -> str:
    """根据quality参数选择模型"""
    if request.quality and request.quality.value == "hd":
        return "hd-model"
    return "standard-model"
```

### 4. 缓存友好

引擎返回的音频数据会自动被系统缓存，无需在引擎层实现缓存逻辑。

### 5. 异步优先

所有I/O操作都应该是异步的：

```python
async with httpx.AsyncClient() as client:
    response = await client.post(url, ...)
```

## 🔍 调试新引擎

### 1. 检查引擎是否注册成功

```bash
# 启动服务器，查看日志
python scripts/quickstart.py

# 应该看到：
# ✓ Registered engine class: elevenlabs -> ElevenLabsTTSEngine
# ✓ Initialized engine: elevenlabs
# ✓ ElevenLabs TTS enabled
```

### 2. 测试引擎健康状态

```bash
curl "http://localhost:8000/api/v1/health"
```

### 3. 获取引擎声音列表

```bash
curl "http://localhost:8000/api/v1/voices?engine=elevenlabs"
```

### 4. 测试语音合成

```bash
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from ElevenLabs!",
    "engine": "elevenlabs",
    "voice": "voice_id_here"
  }'
```

## 📚 参考资源

- **抽象基类**: `packages/core/engine_base.py`
- **引擎管理器**: `packages/core/engine_manager.py`
- **示例实现**: `packages/engines/edge_tts_engine.py`
- **OpenAI实现**: `packages/engines/openai_tts_engine.py` (有质量控制示例)
- **配置管理**: `packages/api/config.py`

## 🚀 总结

TTS System 采用**高度模块化的插件式架构**，添加新引擎的工作量极小：

- ⏱️ **开发时间**: 30-60分钟（包括测试）
- 📝 **代码行数**: ~150-200行（包含完整功能）
- 🔧 **修改位置**: 5个文件
- 🎯 **核心代码**: 零修改

**可扩展性评分**: ⭐⭐⭐⭐⭐ (5/5)

系统已经为未来扩展做好了充分准备，可以轻松支持任何新的TTS服务！
