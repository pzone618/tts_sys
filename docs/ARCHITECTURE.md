# TTS 系统架构

本文档描述 TTS 系统的整体架构和设计模式。

## 🏗️ 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     API Routes                           │    │
│  │  • /api/v1/tts/generate                                 │    │
│  │  • /api/v1/voices                                       │    │
│  │  • /api/v1/history                                      │    │
│  └────────────────────┬────────────────────────────────────┘    │
│                       │                                           │
│  ┌────────────────────▼────────────────────────────────────┐    │
│  │              Engine Manager (Singleton)                  │    │
│  │  • 引擎注册和生命周期管理                                │    │
│  │  • 引擎健康检查                                           │    │
│  │  • 统一的引擎访问接口                                     │    │
│  └────────────────────┬────────────────────────────────────┘    │
│                       │                                           │
└───────────────────────┼───────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Edge TTS     │ │  OpenAI TTS   │ │  Youdao TTS   │  ... 可扩展
│   Engine      │ │   Engine      │ │   Engine      │
└───────────────┘ └───────────────┘ └───────────────┘
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
            ┌─────────────────────┐
            │  TTSEngineBase      │
            │  (Abstract Base)    │
            │                     │
            │  • engine_name()    │
            │  • synthesize()     │
            │  • get_voices()     │
            └─────────────────────┘
```

## 📦 模块结构

### 1. **packages/shared** - 共享层
包含所有模块共用的类型、模型和工具。

```
shared/
├── models.py        # Pydantic 数据模型
│   ├── TTSRequest
│   ├── TTSResponse
│   ├── Voice
│   └── HistoryRecord
├── enums.py         # 枚举和常量
│   ├── TTSEngine
│   ├── AudioFormat
│   ├── AudioQuality
│   └── VoiceGender
└── utils.py         # 辅助函数
```

**职责**: 定义数据契约，确保类型安全

### 2. **packages/core** - 核心层
系统的业务逻辑核心。

```
core/
├── engine_base.py      # 引擎抽象基类
├── engine_manager.py   # 引擎管理器
├── audio_processor.py  # 音频处理
└── cache_manager.py    # 缓存管理
```

**职责**: 
- 定义引擎接口标准
- 管理引擎生命周期
- 提供通用服务（缓存、音频处理）

### 3. **packages/engines** - 引擎层
各TTS引擎的具体实现。

```
engines/
├── edge_tts_engine.py      # Microsoft Edge TTS
├── openai_tts_engine.py    # OpenAI TTS
├── youdao_tts_engine.py    # Youdao TTS
├── azure_tts_engine.py     # Azure Cognitive Services
└── google_tts_engine.py    # Google Cloud TTS
```

**职责**: 
- 实现具体TTS服务的API调用
- 处理各引擎特定的参数
- 转换引擎响应为统一格式

### 4. **packages/api** - 接口层
FastAPI 应用和路由。

```
api/
├── main.py          # 应用入口
├── config.py        # 配置管理
├── database.py      # 数据库设置
└── routes/          # API 路由
    ├── tts.py       # TTS 生成端点
    ├── voices.py    # 声音查询端点
    └── history.py   # 历史记录端点
```

**职责**: 
- 暴露RESTful API
- 请求验证和响应格式化
- 路由管理

## 🎯 设计模式

### 1. **抽象工厂模式 (Abstract Factory)**

`TTSEngineBase` 定义了创建TTS引擎的接口：

```python
class TTSEngineBase(ABC):
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> bytes:
        """每个引擎必须实现此方法"""
        pass
```

### 2. **单例模式 (Singleton)**

`EngineManager` 作为全局单例管理所有引擎：

```python
# packages/core/engine_manager.py
engine_manager = EngineManager()  # 全局唯一实例
```

### 3. **策略模式 (Strategy)**

不同的TTS引擎作为不同的策略，可以在运行时切换：

```python
# 用户通过 request.engine 选择策略
engine = engine_manager.get_engine(request.engine)
audio = await engine.synthesize(request)
```

### 4. **依赖注入 (Dependency Injection)**

通过配置注入引擎依赖：

```python
# 在 main.py 启动时注入配置
engine_manager.initialize_engine(
    TTSEngine.OPENAI, 
    settings.get_engine_config("openai")  # 注入API key等
)
```

### 5. **模板方法模式 (Template Method)**

基类提供通用逻辑，子类实现具体细节：

```python
class TTSEngineBase:
    async def health_check(self) -> bool:
        """模板方法：基类实现通用健康检查"""
        voices = await self.get_voices()  # 调用子类实现
        return len(voices) > 0
```

## 🔄 请求处理流程

### 语音生成请求流程

```
1. HTTP Request
   POST /api/v1/tts/generate
   {
     "text": "Hello",
     "engine": "openai",
     "voice": "nova"
   }
   
2. API Route (tts.py)
   ├─ 请求验证 (Pydantic)
   └─ 调用 Engine Manager
   
3. Engine Manager
   ├─ 获取指定引擎实例
   ├─ 检查引擎是否启用
   └─ 委托给具体引擎
   
4. OpenAI TTS Engine
   ├─ 构建 API 请求
   ├─ 调用 OpenAI API
   ├─ 处理响应
   └─ 返回音频数据
   
5. Cache & Storage
   ├─ 计算缓存 key
   ├─ 保存音频文件
   └─ 记录到数据库
   
6. HTTP Response
   {
     "request_id": "...",
     "audio_url": "/api/v1/audio/abc123.mp3",
     "cached": false,
     "processing_time_ms": 342.5
   }
```

## 🔌 可扩展性设计

### 水平扩展 - 添加新引擎

**零侵入性**: 添加新引擎不需要修改任何现有代码

```python
# 1. 创建新引擎类
class NewTTSEngine(TTSEngineBase):
    # 实现必需方法
    pass

# 2. 在 main.py 注册
engine_manager.register_engine_class(
    TTSEngine.NEW, 
    NewTTSEngine
)

# 3. 在 .env 启用
NEW_TTS_ENABLED=true
NEW_API_KEY=xxx
```

### 垂直扩展 - 添加新功能

**功能扩展点**:

1. **新的音频参数**: 在 `TTSRequest` 模型添加字段
2. **新的路由**: 在 `api/routes/` 添加新文件
3. **新的数据库表**: 使用 Alembic 创建迁移
4. **新的缓存策略**: 在 `cache_manager.py` 扩展

## 🛡️ 错误处理层次

```
API Layer (routes/)
  ├─ HTTPException (400, 404, 422)
  └─ 传递给 Engine Manager

Engine Manager Layer
  ├─ ValueError (引擎未找到/未启用)
  └─ 传递给具体引擎

Engine Layer
  ├─ RuntimeError (API 调用失败)
  ├─ httpx.HTTPError (网络错误)
  └─ 记录日志并向上抛出

Exception Middleware
  ├─ 捕获所有未处理异常
  ├─ 记录详细日志
  └─ 返回统一错误响应
```

## 📊 数据流

### 配置流

```
.env 文件
  ↓
Settings (config.py)
  ↓
Engine Manager
  ↓
具体 Engine 实例
```

### 数据流

```
用户请求 (JSON)
  ↓
Pydantic 验证 (TTSRequest)
  ↓
Engine 处理
  ↓
音频数据 (bytes)
  ↓
文件存储 + 数据库记录
  ↓
响应 (TTSResponse)
```

## 🔍 核心接口

### TTSEngineBase Interface

```python
class TTSEngineBase(ABC):
    """所有引擎必须实现的接口"""
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎标识符"""
    
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> bytes:
        """核心方法：文本转语音"""
    
    @abstractmethod
    async def get_voices(self, language: str | None = None) -> list[Voice]:
        """获取可用声音"""
    
    # 以下方法有默认实现，可选重写
    async def validate_voice(self, voice_id: str) -> bool:
        """验证声音ID"""
    
    async def health_check(self) -> bool:
        """健康检查"""
```

## 💾 持久化

### 数据库表

**tts_requests** - 请求历史
```sql
CREATE TABLE tts_requests (
    id INTEGER PRIMARY KEY,
    request_id VARCHAR(36) UNIQUE,
    text TEXT,
    engine VARCHAR(50),
    voice VARCHAR(100),
    format VARCHAR(10),
    quality VARCHAR(20),
    bitrate INTEGER,
    sample_rate INTEGER,
    cache_key VARCHAR(64),
    cached BOOLEAN,
    status VARCHAR(20),
    audio_path TEXT,
    size_bytes INTEGER,
    processing_time_ms FLOAT,
    created_at TIMESTAMP
);

-- 索引优化查询
CREATE INDEX idx_engine ON tts_requests(engine);
CREATE INDEX idx_cached ON tts_requests(cached);
CREATE INDEX idx_created_at ON tts_requests(created_at);
```

## 🚀 性能优化

### 1. 异步 I/O
- 所有引擎使用 `async/await`
- 支持高并发请求

### 2. 智能缓存
- 基于内容哈希的缓存key
- 可配置TTL (默认30天)
- 自动清理过期缓存

### 3. 连接池
- httpx AsyncClient 复用
- 减少连接开销

### 4. 数据库优化
- SQLAlchemy 异步模式
- 合理的索引设计
- 批量查询优化

## 🔒 安全考虑

### 1. API Key 管理
- 所有密钥存储在 `.env`
- 不在日志中输出敏感信息
- 支持通过环境变量注入

### 2. 输入验证
- Pydantic 严格验证
- 文本长度限制
- 参数范围检查

### 3. 错误信息
- 不泄露内部实现细节
- 统一的错误响应格式

## 📈 监控和日志

### 日志级别
- `INFO`: 正常操作（引擎初始化、请求完成）
- `WARNING`: 可恢复问题（引擎禁用、缓存失效）
- `ERROR`: 需要关注的错误（API调用失败、语音合成失败）

### 可观测性
- 请求历史完整记录
- 统计信息 API
- 缓存命中率跟踪
- 引擎健康状态监控

## 🎓 总结

TTS System 的架构特点：

1. ✅ **高度模块化** - 清晰的层次划分
2. ✅ **松耦合** - 模块间依赖最小化
3. ✅ **易扩展** - 插件式引擎架构
4. ✅ **类型安全** - 完整的类型提示
5. ✅ **异步优先** - 高性能并发处理
6. ✅ **生产就绪** - 缓存、日志、错误处理完善

**可维护性评分**: ⭐⭐⭐⭐⭐ (5/5)
