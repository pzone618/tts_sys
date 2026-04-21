# 🚀 快速开始指南

欢迎使用 TTS System！这是一个 5 分钟的快速上手指南。

## ⚡ 最快的开始方式

```bash
# 1. 确保你在项目目录中
cd c:\Work\dev\tts_sys

# 2. 运行快速启动脚本
python scripts/quickstart.py
```

就这么简单！脚本会自动：
- ✅ 检查 uv 是否安装
- ✅ 安装所有依赖
- ✅ 创建 .env 配置文件
- ✅ 初始化数据库
- ✅ 启动 API 服务器

服务器启动后（默认端口 8000，可在 .env 中通过 API_PORT 配置）：
- 🌐 API 地址: http://localhost:<API_PORT>
- 📚 API 文档: http://localhost:<API_PORT>/api/v1/docs
- 🔍 ReDoc: http://localhost:<API_PORT>/api/v1/redoc

## 🎯 第一次测试

### 1. 在浏览器中测试

打开 http://localhost:8000/api/v1/docs

点击 `/api/v1/tts/generate` 端点的 "Try it out"，使用以下测试数据：

```json
{
  "text": "你好，这是一个测试。",
  "engine": "edge",
  "voice": "zh-CN-XiaoxiaoNeural",
  "rate": 1.0,
  "volume": 1.0,
  "pitch": 1.0,
  "format": "mp3"
}
```

### 2. 使用 curl 测试

```bash
curl -X POST "http://localhost:8000/api/v1/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "engine": "edge",
    "voice": "en-US-JennyNeural",
    "rate": 1.0,
    "volume": 1.0,
    "format": "mp3"
  }'
```

### 3. 查看可用的声音

```bash
# 查看所有声音
curl "http://localhost:8000/api/v1/voices"

# 查看中文声音
curl "http://localhost:8000/api/v1/voices?language=zh-CN"

# 查看英文声音
curl "http://localhost:8000/api/v1/voices?language=en-US"
```

## 🔧 手动安装步骤（如果需要）

如果快速启动脚本不工作，可以手动执行：

```bash
# 1. 安装 uv（如果未安装）
# Windows (PowerShell):
irm https://astral.sh/uv/install.ps1 | iex

# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 安装依赖
uv sync

# 3. 创建配置文件
cp .env.example .env
# 可选：编辑 .env 修改 API_PORT（默认：8000）

# 4. 初始化数据库
uv run alembic upgrade head

# 5. 启动服务器（使用 .env 中配置的端口）
make run
# 或手动指定
uv run uvicorn packages.api.main:app --reload --host 0.0.0.0 --port ${API_PORT:-8000}
```

## 🎨 使用不同的 TTS 引擎

### Edge TTS (默认，免费)

Edge TTS 默认启用，不需要任何配置！

```python
{
  "engine": "edge",
  "voice": "zh-CN-XiaoxiaoNeural"  # 中文女声
}
```

推荐声音：
- 中文：`zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`, `zh-CN-YunyangNeural`
- 英文：`en-US-JennyNeural`, `en-US-GuyNeural`, `en-GB-SoniaNeural`
- 日语：`ja-JP-NanamiNeural`, `ja-JP-KeitaNeural`

### OpenAI TTS (高质量)

1. 编辑 `.env` 文件：
```env
OPENAI_TTS_ENABLED=true
OPENAI_API_KEY=sk-your-api-key-here
```

2. 重启服务器

3. 使用 OpenAI：
```python
{
  "engine": "openai",
  "voice": "alloy"  # 可选: alloy, echo, fable, onyx, nova, shimmer
}
```

### Youdao TTS (中文)

1. 在有道智云注册获取 API Key: https://ai.youdao.com/

2. 编辑 `.env` 文件：
```env
YOUDAO_TTS_ENABLED=true
YOUDAO_APP_KEY=your-app-key
YOUDAO_APP_SECRET=your-app-secret
```

3. 重启服务器

## 🐛 常见问题

### Q: 端口 8000 被占用？
```bash
# Windows
netstat -ano | findstr :8000
# 找到 PID，然后
taskkill /F /PID <pid>

# Linux/Mac
lsof -i :8000
kill -9 <pid>

# 或者使用不同端口
uv run uvicorn packages.api.main:app --port 8001
```

### Q: uv 命令找不到？
确保 uv 已正确安装并添加到 PATH：
```bash
# 检查安装
uv --version

# 重新加载环境变量（Windows）
refreshenv

# 重新加载环境变量（Linux/Mac）
source ~/.bashrc  # or ~/.zshrc
```

### Q: 数据库初始化失败？
```bash
# 删除旧数据库
rm database/tts_sys.db

# 重新初始化
uv run alembic upgrade head
```

### Q: 需要更改存储路径？
编辑 `.env` 文件：
```env
STORAGE_PATH=D:/tts_storage  # 使用绝对路径
```

## 📚 下一步

- 📖 阅读完整 API 文档: [docs/API.md](docs/API.md)
- 🚀 查看部署指南: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 🤝 贡献代码: [CONTRIBUTING.md](CONTRIBUTING.md)
- 🐳 使用 Docker: `docker-compose up -d`

## 💡 使用技巧

1. **缓存加速**: 相同的文本和参数会自动使用缓存，第二次请求几乎是瞬间返回

2. **批量处理**: API 完全支持并发请求，可以同时发送多个 TTS 请求

3. **音频参数**: 调整 `rate`（语速）、`volume`（音量）、`pitch`（音调）获得不同效果

4. **格式选择**: 支持 mp3, wav, ogg, opus, aac 等多种格式

5. **声音搜索**: 使用 `/voices` 端点的 `search` 参数查找特定声音

## 🎉 开始使用

一切准备就绪！现在你可以：
- 访问 http://localhost:8000/api/v1/docs 查看交互式文档
- 开始构建你的 TTS 应用
- 集成到你的项目中

祝你使用愉快！如有问题，欢迎提 Issue。
