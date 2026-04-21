# TTS 引擎降级与容错方案

## 🎯 问题场景

当基于 HTTP API 的在线TTS服务遭遇：
- ❌ 网络连接问题
- ❌ API 服务不可用
- ❌ 超时或限流
- ❌ API Key 失效

系统应该能够**自动降级到离线本地引擎**，保证服务的高可用性。

## 🛡️ 解决方案架构

```
┌─────────────────────────────────────────────────────────────┐
│                     TTS 请求                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   引擎降级策略管理器           │
        │   Engine Fallback Manager     │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────┐              ┌──────────────┐
│  熔断器监控   │              │  降级链配置   │
│  Circuit      │              │  Fallback     │
│  Breaker     │              │  Chain        │
└──────┬───────┘              └──────┬───────┘
       │                             │
       └─────────────┬───────────────┘
                     │
        ┌────────────┴──────────────┐
        │                           │
        ▼                           ▼
┌─────────────┐           ┌──────────────┐
│ 在线引擎     │  失败→    │ 离线引擎      │
│ OpenAI TTS  │ ──────→   │ pyttsx3      │
│ ElevenLabs  │           │ edge-tts      │
│ Azure TTS   │           │ (本地缓存)     │
└─────────────┘           └──────────────┘
```

## 📋 方案一：引擎优先级链

### 实现：在请求参数中配置降级链

```python
# packages/shared/models.py

class TTSRequest(BaseModel):
    """TTS synthesis request model."""
    
    text: str = Field(...)
    engine: TTSEngine = Field(...)  # 主引擎
    voice: str = Field(...)
    
    # 降级配置（新增）
    fallback_engines: list[TTSEngine] | None = Field(
        default=None,
        description="Fallback engines to try if primary fails"
    )
    enable_auto_fallback: bool = Field(
        default=True,
        description="Enable automatic fallback to offline engines"
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Max retry attempts per engine"
    )
    
    # ... 其他字段 ...
```

### 使用示例

```bash
# 方式1：自动降级（推荐）
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "openai",
    "voice": "nova",
    "enable_auto_fallback": true
  }'

# 方式2：手动指定降级链
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "openai",
    "voice": "nova",
    "fallback_engines": ["edge", "pyttsx3"]
  }'
```

## 📋 方案二：熔断器模式 (Circuit Breaker)

### 核心实现

```python
# packages/core/circuit_breaker.py

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict
from loguru import logger


class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态（不可用）
    HALF_OPEN = "half_open"  # 半开状态（尝试恢复）


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5  # 失败阈值
    success_threshold: int = 2  # 恢复成功阈值
    timeout_seconds: int = 60   # 熔断超时时间
    half_open_timeout: int = 30 # 半开超时时间


@dataclass
class CircuitStats:
    """熔断器统计信息"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    state: CircuitState = CircuitState.CLOSED


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitBreakerConfig | None = None):
        """Initialize circuit breaker."""
        self.config = config or CircuitBreakerConfig()
        self.stats: Dict[str, CircuitStats] = {}
    
    def get_state(self, engine_name: str) -> CircuitState:
        """获取引擎的熔断器状态"""
        if engine_name not in self.stats:
            self.stats[engine_name] = CircuitStats()
        
        stats = self.stats[engine_name]
        current_time = time.time()
        
        # 检查是否应该从 OPEN 转到 HALF_OPEN
        if stats.state == CircuitState.OPEN:
            if current_time - stats.last_failure_time > self.config.timeout_seconds:
                logger.info(f"Circuit breaker for {engine_name} entering HALF_OPEN state")
                stats.state = CircuitState.HALF_OPEN
                stats.success_count = 0
        
        return stats.state
    
    def is_available(self, engine_name: str) -> bool:
        """检查引擎是否可用"""
        state = self.get_state(engine_name)
        return state != CircuitState.OPEN
    
    def record_success(self, engine_name: str) -> None:
        """记录成功"""
        if engine_name not in self.stats:
            self.stats[engine_name] = CircuitStats()
        
        stats = self.stats[engine_name]
        stats.success_count += 1
        stats.last_success_time = time.time()
        
        # HALF_OPEN 状态下，连续成功后恢复到 CLOSED
        if stats.state == CircuitState.HALF_OPEN:
            if stats.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker for {engine_name} recovered to CLOSED")
                stats.state = CircuitState.CLOSED
                stats.failure_count = 0
        
        # CLOSED 状态下，重置失败计数
        if stats.state == CircuitState.CLOSED:
            stats.failure_count = 0
    
    def record_failure(self, engine_name: str) -> None:
        """记录失败"""
        if engine_name not in self.stats:
            self.stats[engine_name] = CircuitStats()
        
        stats = self.stats[engine_name]
        stats.failure_count += 1
        stats.last_failure_time = time.time()
        
        # 达到失败阈值，打开熔断器
        if stats.failure_count >= self.config.failure_threshold:
            logger.warning(
                f"Circuit breaker OPENED for {engine_name} "
                f"after {stats.failure_count} failures"
            )
            stats.state = CircuitState.OPEN
        
        # HALF_OPEN 状态下，任何失败都重新打开熔断器
        if stats.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker for {engine_name} reopened")
            stats.state = CircuitState.OPEN
    
    def reset(self, engine_name: str) -> None:
        """重置熔断器"""
        if engine_name in self.stats:
            self.stats[engine_name] = CircuitStats()
            logger.info(f"Circuit breaker reset for {engine_name}")
    
    def get_stats(self) -> Dict[str, dict]:
        """获取所有引擎的统计信息"""
        return {
            name: {
                "state": stats.state.value,
                "failure_count": stats.failure_count,
                "success_count": stats.success_count,
                "last_failure": stats.last_failure_time,
                "last_success": stats.last_success_time,
            }
            for name, stats in self.stats.items()
        }


# 全局实例
circuit_breaker = CircuitBreaker()
```

## 📋 方案三：增强的引擎管理器

```python
# packages/core/engine_manager.py (增强版本)

from typing import Type, List
from loguru import logger

from packages.shared.enums import TTSEngine
from packages.shared.models import TTSRequest, Voice
from .engine_base import TTSEngineBase
from .circuit_breaker import circuit_breaker, CircuitState


class EngineManager:
    """增强版引擎管理器，支持降级和容错"""
    
    def __init__(self) -> None:
        """Initialize engine manager."""
        self._engines: dict[TTSEngine, TTSEngineBase] = {}
        self._engine_classes: dict[TTSEngine, Type[TTSEngineBase]] = {}
        
        # 引擎分类：在线引擎和离线引擎
        self._online_engines: set[TTSEngine] = {
            TTSEngine.OPENAI, 
            TTSEngine.AZURE, 
            TTSEngine.GOOGLE,
            TTSEngine.YOUDAO
        }
        self._offline_engines: set[TTSEngine] = {
            TTSEngine.EDGE,      # edge-tts 可以缓存
            TTSEngine.PYTTSX3,   # 本地TTS引擎
        }
    
    # ... 原有方法保持不变 ...
    
    def is_online_engine(self, engine_type: TTSEngine) -> bool:
        """检查是否为在线引擎"""
        return engine_type in self._online_engines
    
    def get_fallback_chain(
        self, 
        primary_engine: TTSEngine,
        custom_fallbacks: List[TTSEngine] | None = None
    ) -> List[TTSEngine]:
        """获取降级链
        
        Args:
            primary_engine: 主引擎
            custom_fallbacks: 自定义降级链
        
        Returns:
            完整的降级链（包含主引擎）
        """
        chain = [primary_engine]
        
        # 使用自定义降级链
        if custom_fallbacks:
            for engine in custom_fallbacks:
                if engine != primary_engine and self.is_engine_available(engine):
                    chain.append(engine)
        else:
            # 默认降级策略
            # 1. 如果主引擎是在线引擎，降级到其他在线引擎
            if self.is_online_engine(primary_engine):
                for engine in self._online_engines:
                    if engine != primary_engine and self.is_engine_available(engine):
                        chain.append(engine)
            
            # 2. 最后降级到离线引擎
            for engine in self._offline_engines:
                if self.is_engine_available(engine):
                    chain.append(engine)
        
        return chain
    
    async def synthesize_with_fallback(
        self,
        request: TTSRequest,
        max_retries: int = 2
    ) -> tuple[bytes, TTSEngine, bool]:
        """带降级的语音合成
        
        Args:
            request: TTS请求
            max_retries: 每个引擎的最大重试次数
        
        Returns:
            (音频数据, 实际使用的引擎, 是否发生了降级)
        
        Raises:
            RuntimeError: 所有引擎都失败
        """
        # 获取降级链
        fallback_chain = self.get_fallback_chain(
            request.engine,
            request.fallback_engines if hasattr(request, 'fallback_engines') else None
        )
        
        logger.info(f"Fallback chain: {[e.value for e in fallback_chain]}")
        
        last_error = None
        used_fallback = False
        
        # 尝试降级链中的每个引擎
        for i, engine_type in enumerate(fallback_chain):
            # 检查熔断器状态
            if not circuit_breaker.is_available(engine_type.value):
                logger.warning(
                    f"Engine {engine_type.value} is circuit broken, skipping"
                )
                continue
            
            if i > 0:
                used_fallback = True
                logger.info(
                    f"Falling back to engine: {engine_type.value} "
                    f"(attempt {i+1}/{len(fallback_chain)})"
                )
            
            # 尝试该引擎（带重试）
            for retry in range(max_retries + 1):
                try:
                    engine = self.get_engine(engine_type)
                    
                    # 修改请求的引擎（如果需要）
                    original_engine = request.engine
                    original_voice = request.voice
                    
                    if engine_type != original_engine:
                        # 降级时需要映射voice
                        request.engine = engine_type
                        request.voice = await self._map_voice_for_engine(
                            original_voice, engine_type
                        )
                    
                    # 执行合成
                    audio_data = await engine.synthesize(request)
                    
                    # 记录成功
                    circuit_breaker.record_success(engine_type.value)
                    
                    logger.info(
                        f"Successfully synthesized with {engine_type.value} "
                        f"(fallback={used_fallback}, retry={retry})"
                    )
                    
                    return audio_data, engine_type, used_fallback
                
                except Exception as e:
                    last_error = e
                    logger.error(
                        f"Engine {engine_type.value} failed "
                        f"(retry {retry+1}/{max_retries+1}): {e}"
                    )
                    
                    # 记录失败
                    circuit_breaker.record_failure(engine_type.value)
                    
                    # 如果还有重试机会，继续
                    if retry < max_retries:
                        continue
                    
                    # 否则尝试下一个引擎
                    break
        
        # 所有引擎都失败了
        error_msg = (
            f"All engines failed. Tried: {[e.value for e in fallback_chain]}. "
            f"Last error: {last_error}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def _map_voice_for_engine(
        self, 
        original_voice: str, 
        target_engine: TTSEngine
    ) -> str:
        """将voice映射到目标引擎
        
        Args:
            original_voice: 原始voice ID
            target_engine: 目标引擎
        
        Returns:
            映射后的voice ID
        """
        try:
            # 尝试获取目标引擎的声音列表
            engine = self.get_engine(target_engine)
            voices = await engine.get_voices()
            
            if not voices:
                # 使用默认voice
                return self._get_default_voice(target_engine)
            
            # 尝试找到相似的voice
            # 策略1: 完全匹配
            for voice in voices:
                if voice.id == original_voice:
                    return voice.id
            
            # 策略2: 语言匹配
            original_lang = original_voice.split("-")[:2]  # e.g., ["en", "US"]
            for voice in voices:
                voice_lang = voice.language.split("-")[:2]
                if voice_lang == original_lang:
                    return voice.id
            
            # 策略3: 返回第一个可用voice
            return voices[0].id
        
        except Exception as e:
            logger.warning(f"Failed to map voice: {e}")
            return self._get_default_voice(target_engine)
    
    def _get_default_voice(self, engine_type: TTSEngine) -> str:
        """获取引擎的默认voice"""
        defaults = {
            TTSEngine.EDGE: "en-US-JennyNeural",
            TTSEngine.OPENAI: "alloy",
            TTSEngine.PYTTSX3: "default",
            TTSEngine.YOUDAO: "0",
        }
        return defaults.get(engine_type, "default")


# 更新全局实例
engine_manager = EngineManager()
```

## 📋 方案四：添加离线TTS引擎

```python
# packages/engines/pyttsx3_engine.py

"""pyttsx3 离线TTS引擎实现"""

import io
import pyttsx3
from loguru import logger

from packages.core.engine_base import TTSEngineBase
from packages.shared.enums import TTSEngine, VoiceGender
from packages.shared.models import TTSRequest, Voice


class Pyttsx3Engine(TTSEngineBase):
    """pyttsx3 本地离线TTS引擎
    
    无需网络连接，作为最终降级选项。
    """
    
    def __init__(self, config: dict[str, str] | None = None) -> None:
        """Initialize pyttsx3 engine."""
        super().__init__(config)
        try:
            self._tts = pyttsx3.init()
            self._voices_cache: list[Voice] | None = None
        except Exception as e:
            logger.warning(f"Failed to initialize pyttsx3: {e}")
            self.disable()
    
    @property
    def engine_name(self) -> str:
        """Return engine name."""
        return TTSEngine.PYTTSX3.value
    
    async def synthesize(self, request: TTSRequest) -> bytes:
        """Synthesize speech using pyttsx3.
        
        Args:
            request: TTS request
        
        Returns:
            Audio data in WAV format
        """
        if not self.is_enabled():
            raise RuntimeError("pyttsx3 engine is not enabled")
        
        try:
            # 设置参数
            self._tts.setProperty('rate', int(request.rate * 150))  # 默认速率150
            self._tts.setProperty('volume', request.volume)
            
            # 设置voice
            voices = self._tts.getProperty('voices')
            if request.voice != "default" and request.voice.isdigit():
                voice_index = int(request.voice)
                if 0 <= voice_index < len(voices):
                    self._tts.setProperty('voice', voices[voice_index].id)
            
            # 保存到内存
            output = io.BytesIO()
            self._tts.save_to_file(request.text, output)
            self._tts.runAndWait()
            
            audio_data = output.getvalue()
            logger.info(f"pyttsx3 synthesis completed: {len(audio_data)} bytes")
            
            return audio_data
        
        except Exception as e:
            logger.error(f"pyttsx3 synthesis failed: {e}")
            raise RuntimeError(f"pyttsx3 synthesis failed: {e}") from e
    
    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """Get available voices from pyttsx3."""
        if self._voices_cache:
            return self._voices_cache
        
        try:
            system_voices = self._tts.getProperty('voices')
            voices = []
            
            for i, sv in enumerate(system_voices):
                voice = Voice(
                    id=str(i),
                    name=sv.name,
                    language=sv.languages[0] if sv.languages else "en-US",
                    gender=VoiceGender.NEUTRAL,
                    engine=TTSEngine.PYTTSX3,
                    description="Local system voice (offline)",
                    tags=["offline", "local", "fallback"],
                )
                voices.append(voice)
            
            self._voices_cache = voices
            return voices
        
        except Exception as e:
            logger.error(f"Failed to get pyttsx3 voices: {e}")
            return []
```

## 📋 方案五：在API路由中集成降级

```python
# packages/api/routes/tts.py (修改 generate_speech 函数)

@router.post("/generate", ...)
async def generate_speech(
    request: TTSRequest,
    db: Session = Depends(get_db),
) -> TTSResponse:
    """Generate speech with automatic fallback"""
    start_time = time.time()
    
    try:
        # 使用降级合成
        audio_data, actual_engine, used_fallback = await engine_manager.synthesize_with_fallback(
            request,
            max_retries=request.max_retries if hasattr(request, 'max_retries') else 2
        )
        
        # 如果发生了降级，记录到响应中
        if used_fallback:
            logger.warning(
                f"Fallback occurred: requested={request.engine.value}, "
                f"actual={actual_engine.value}"
            )
        
        # ... 保存音频文件和数据库记录 ...
        
        # 在响应中添加降级信息
        response = TTSResponse(
            # ... 其他字段 ...
            metadata={
                "requested_engine": request.engine.value,
                "actual_engine": actual_engine.value,
                "fallback_occurred": used_fallback,
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

## 🎯 配置和使用

### 环境变量配置

```env
# .env

# 降级配置
TTS_ENABLE_AUTO_FALLBACK=true
TTS_MAX_RETRIES=2

# 熔断器配置
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2

# 启用离线引擎
PYTTSX3_ENABLED=true
EDGE_TTS_ENABLED=true
```

### API调用示例

```bash
# 示例1: 使用默认降级
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "openai",
    "voice": "nova",
    "enable_auto_fallback": true
  }'

# 响应（发生降级）:
{
  "request_id": "...",
  "audio_url": "/api/v1/audio/abc123.mp3",
  "status": "completed",
  "metadata": {
    "requested_engine": "openai",
    "actual_engine": "edge",
    "fallback_occurred": true
  }
}

# 示例2: 自定义降级链
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，世界",
    "engine": "openai",
    "voice": "nova",
    "fallback_engines": ["youdao", "edge", "pyttsx3"],
    "max_retries": 1
  }'
```

### 监控熔断器状态

```bash
# 新增端点：查看熔断器状态
curl "http://localhost:8000/api/v1/system/circuit-breaker"

# 响应:
{
  "openai": {
    "state": "open",
    "failure_count": 5,
    "success_count": 0,
    "last_failure": 1234567890.0
  },
  "edge": {
    "state": "closed",
    "failure_count": 0,
    "success_count": 10,
    "last_success": 1234567895.0
  }
}
```

## 📊 降级策略总结

| 场景 | 降级路径 | 说明 |
|------|---------|------|
| OpenAI 失败 | OpenAI → Azure → Google → Edge → pyttsx3 | 优先使用其他云服务 |
| 所有在线服务失败 | 在线 → Edge (预缓存) → pyttsx3 | 最终使用本地引擎 |
| 网络完全断开 | 直接使用 pyttsx3 | 离线模式 |
| 熔断器打开 | 跳过被熔断引擎 | 自动跳过故障引擎 |

## ✅ 优势

1. **零停机** - 即使所有在线服务失败，仍可使用本地引擎
2. **自动恢复** - 熔断器自动尝试恢复故障引擎
3. **灵活配置** - 支持默认策略和自定义降级链
4. **透明性** - API响应包含降级信息
5. **可观测** - 完整的日志和监控

## 🚀 实施步骤

1. 添加 `circuit_breaker.py` 和 `pyttsx3_engine.py`
2. 更新 `engine_manager.py` 增强降级功能
3. 修改 `TTSRequest` 模型添加降级参数
4. 更新 API 路由集成降级逻辑
5. 添加熔断器监控端点
6. 配置环境变量
7. 编写测试用例

这个方案提供了**企业级的高可用性保障**！
