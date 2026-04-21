# API 文档

> **注意**: 本文档中的所有示例使用默认端口 8000。如果您在 `.env` 文件中配置了不同的 `API_PORT`，请相应替换端口号。

## 快速开始

### 1. 生成语音

```bash
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是一个测试。",
    "engine": "edge",
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": 1.0,
    "volume": 1.0,
    "format": "mp3",
    "quality": "high"
  }'
```

响应：
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "audio_url": "/api/v1/audio/abc123.mp3",
  "size_bytes": 48000,
  "format": "mp3",
  "status": "completed",
  "cached": false,
  "processing_time_ms": 342.5,
  "created_at": "2026-04-21T10:30:00Z"
}
```

### 2. 查询可用声音

```bash
# 查询所有声音
curl "http://localhost:8000/api/v1/voices"

# 按引擎过滤
curl "http://localhost:8000/api/v1/voices?engine=edge"

# 按语言过滤
curl "http://localhost:8000/api/v1/voices?language=zh-CN"

# 按性别过滤
curl "http://localhost:8000/api/v1/voices?gender=female"

# 搜索
curl "http://localhost:8000/api/v1/voices?search=xiaoxiao"
```

### 3. 查询历史记录

```bash
# 获取最近的请求
curl "http://localhost:8000/api/v1/history?limit=10"

# 按引擎过滤
curl "http://localhost:8000/api/v1/history?engine=edge"

# 按时间过滤
curl "http://localhost:8000/api/v1/history?from_date=2026-04-01T00:00:00Z"
```

### 4. 查询统计信息

```bash
curl "http://localhost:8000/api/v1/history/stats"
```

响应：
```json
{
  "total_requests": 1250,
  "by_engine": {
    "edge": 800,
    "youdao": 300,
    "openai": 150
  },
  "by_status": {
    "completed": 1200,
    "failed": 50
  },
  "cache_hit_rate_percent": 45.5,
  "avg_processing_time_ms": 285.3,
  "total_audio_size_bytes": 52428800
}
```

## API 端点

### TTS API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/tts/generate` | 生成语音 |
| GET | `/api/v1/tts/cache/stats` | 缓存统计 |
| DELETE | `/api/v1/tts/cache/clear` | 清空缓存 |
| POST | `/api/v1/tts/cache/cleanup` | 清理过期缓存 |

### 声音 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/voices` | 列出可用声音 |
| GET | `/api/v1/voices/{voice_id}` | 获取声音详情 |

### 历史 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/history` | 获取历史记录 |
| GET | `/api/v1/history/stats` | 获取统计信息 |

### 系统 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/docs` | API 文档 |

## 支持的 TTS 引擎

### 1. Edge TTS (Microsoft)

- **免费，无需 API Key**
- 支持 100+ 种声音
- 多语言支持
- 神经网络语音

推荐声音：
- 中文：`zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`
- 英文：`en-US-JennyNeural`, `en-US-GuyNeural`

### 2. Youdao TTS (有道)

- 需要有道智云 API Key
- 支持中文
- 提供情感语音

配置：
```env
YOUDAO_TTS_ENABLED=true
YOUDAO_APP_KEY=your_app_key
YOUDAO_APP_SECRET=your_app_secret
```

### 3. OpenAI TTS

- 需要 OpenAI API Key
- 6 种高质量声音
- 支持多语言

配置：
```env
OPENAI_TTS_ENABLED=true
OPENAI_API_KEY=your_api_key
OPENAI_TTS_MODEL=tts-1  # or tts-1-hd
```

## 音频参数

### rate (语速)
- 范围：0.5 - 2.0
- 默认：1.0
- 1.5 = 150% 速度
- 0.5 = 50% 速度

### volume (音量)
- 范围：0.0 - 2.0
- 默认：1.0
- 2.0 = 200% 音量

### pitch (音调)
- 范围：0.5 - 2.0
- 默认：1.0
- 1.5 = 高音调
- 0.5 = 低音调

### format (格式)
支持的格式：
- `mp3` (推荐)
- `wav`
- `ogg`
- `opus`
- `aac`

### quality (音频质量预设)
质量等级：
- `standard` - 标准质量，处理速度快
- `high` - 高质量
- `hd` - 高清质量（支持的引擎）

**引擎支持情况：**
- **Edge TTS**: 使用固定质量，质量参数仅记录
- **OpenAI TTS**: 
  - `standard`/`high` → 使用 `tts-1` 模型
  - `hd` → 使用 `tts-1-hd` 模型
- **Youdao TTS**: 使用固定质量，质量参数仅记录

### bitrate (比特率)
- 范围：32 - 320 kbps
- 默认：128 kbps
- 说明：如果设置了 `quality`，该参数将被忽略
- 质量预设映射：
  - `standard` = 128 kbps
  - `high` = 192 kbps
  - `hd` = 256 kbps

### sample_rate (采样率)
- 范围：8000 - 48000 Hz
- 默认：24000 Hz
- 说明：如果设置了 `quality`，该参数将被忽略
- 质量预设映射：
  - `standard` = 24 kHz
  - `high` = 24 kHz
  - `hd` = 48 kHz

**使用建议：**
- 简单场景：只设置 `quality` 参数
- 高级场景：直接设置 `bitrate` 和 `sample_rate` 获得精确控制

## Python SDK 示例

```python
import httpx
import asyncio

async def generate_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural"):
    """生成语音"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/tts/generate",
            json={
                "text": text,
                "engine": "edge",
                "voice": voice,
                "rate": 1.0,
                "volume": 1.0,
                "format": "mp3",
                "quality": "high"  # 使用高质量
            }
        )
        response.raise_for_status()
        result = response.json()
        
        # 下载音频
        audio_url = f"http://localhost:8000{result['audio_url']}"
        audio_response = await client.get(audio_url)
        
        # 保存到文件
        with open("output.mp3", "wb") as f:
            f.write(audio_response.content)
        
        return result

# 使用
asyncio.run(generate_speech("你好，世界！"))
```

## JavaScript/TypeScript 示例

```typescript
interface TTSRequest {
  text: string;
  engine: 'edge' | 'youdao' | 'openai';
  voice: string;
  rate?: number;
  volume?: number;
  pitch?: number;
  format?: 'mp3' | 'wav' | 'ogg';
  quality?: 'standard' | 'high' | 'hd';
  bitrate?: number;  // 32-320 kbps
  sample_rate?: number;  // 8000-48000 Hz
}

async function generateSpeech(request: TTSRequest): Promise<Blob> {
  // 生成语音
  const response = await fetch('http://localhost:8000/api/v1/tts/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  const result = await response.json();

  // 下载音频
  const audioResponse = await fetch(`http://localhost:8000${result.audio_url}`);
  return await audioResponse.blob();
}

// 使用
async function example() {
  // 示例 1：使用质量预设（推荐）
  const audioBlob1 = await generateSpeech({
    text: 'Hello, world!',
    engine: 'openai',
    voice: 'nova',
    quality: 'hd',  // 使用 HD 质量
  });

  // 示例 2：精确控制参数
  const audioBlob2 = await generateSpeech({
    text: 'Hello, world!',
    engine: 'edge',
    voice: 'en-US-JennyNeural',
    bitrate: 192,      // 192 kbps
    sample_rate: 24000, // 24 kHz
  });

  // 播放音频
  const audioUrl = URL.createObjectURL(audioBlob1);
  const audio = new Audio(audioUrl);
  audio.play();
}
```

## 错误处理

API 使用标准 HTTP 状态码：

- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源未找到
- `422`: 验证错误
- `500`: 服务器错误

错误响应格式：
```json
{
  "error": "validation_error",
  "message": "Invalid voice ID",
  "details": {
    "voice": "Voice not found: invalid-voice"
  }
}
```

## 性能优化

### 缓存策略

系统自动缓存相同参数的 TTS 请求：
- 缓存基于文本内容、引擎、声音、参数的哈希值
- 默认缓存 TTL：30 天
- 可通过 `use_cache=false` 禁用缓存

### 并发处理

API 支持高并发请求：
- 异步处理所有 I/O 操作
- 生产环境建议使用多 worker：
  ```bash
  uvicorn packages.api.main:app --workers 4
  ```

### 速率限制

默认配置：
- 每分钟 60 个请求
- 可通过环境变量调整：`RATE_LIMIT_PER_MINUTE`

## 更多信息

- 完整 API 文档：`http://localhost:<API_PORT>/api/v1/docs`（默认端口：8000）
- 端口配置：在 `.env` 文件中设置 `API_PORT` 变量
- GitHub 仓库：[您的仓库地址]
- 问题反馈：[Issues 页面]
