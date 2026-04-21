# 故障排查指南 (Troubleshooting Guide)

本文档帮助你诊断和解决 TTS System 的常见问题。

## 📑 目录

- [安装问题](#安装问题)
- [启动问题](#启动问题)
- [API 错误](#api-错误)
- [引擎问题](#引擎问题)
- [数据库问题](#数据库问题)
- [性能问题](#性能问题)
- [Docker 问题](#docker-问题)

---

## 安装问题

### ❌ `uv` 命令未找到

**症状：**
```bash
uv: command not found
```

**解决方案：**

**Windows:**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
# 重启终端
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# 添加到 PATH
export PATH="$HOME/.local/bin:$PATH"
```

### ❌ Python 版本不匹配

**症状：**
```
Python 3.13+ is required
```

**解决方案：**
```bash
# 检查 Python 版本
python --version

# 安装 Python 3.13
# Windows: 从 python.org 下载
# Linux: pyenv install 3.13.8
# macOS: brew install python@3.13
```

### ❌ 依赖安装失败

**症状：**
```
Failed to build package
```

**解决方案：**
```bash
# 清理缓存
uv cache clean

# 重新同步
uv sync --reinstall

# 如果是特定包失败，手动安装
uv pip install <package-name> --no-cache
```

---

## 启动问题

### ❌ 端口已被占用

**症状：**
```
OSError: [Errno 48] Address already in use
```

**解决方案：**

**方法 1: 修改端口**
```bash
# 编辑 .env
API_PORT=8001

# 或命令行指定
uv run uvicorn packages.api.main:app --port 8001
```

**方法 2: 释放端口**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

### ❌ 数据库未初始化

**症状：**
```
sqlite3.OperationalError: no such table: tts_requests
```

**解决方案：**
```bash
# 运行迁移
uv run alembic upgrade head

# 如果失败，重新初始化
rm database/*.db
uv run alembic upgrade head
```

### ❌ 存储目录不存在

**症状：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'storage/cache'
```

**解决方案：**
```bash
# 创建必要目录
mkdir -p storage/cache storage/temp database

# 或使用 Makefile
make setup
```

---

## API 错误

### ❌ 500 Internal Server Error

**症状：**
API 请求返回 500 错误

**诊断步骤：**

1. **查看日志**
   ```bash
   # 开发模式会显示详细错误
   make run
   ```

2. **检查 .env 配置**
   ```bash
   cat .env
   # 确保必要的配置项存在
   ```

3. **测试健康检查**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

### ❌ 422 Unprocessable Entity

**症状：**
```json
{
  "detail": [
    {
      "loc": ["body", "text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**解决方案：**
检查请求格式，必需字段：
```json
{
  "text": "必需: 要合成的文本",
  "engine": "必需: edge/openai/youdao",
  "voice": "必需: 声音ID"
}
```

### ❌ 429 Too Many Requests

**症状：**
```json
{
  "detail": "Rate limit exceeded"
}
```

**解决方案：**
```bash
# 方法 1: 调整限流设置
# 编辑 .env
RATE_LIMIT_PER_MINUTE=120

# 方法 2: 禁用限流（不推荐生产环境）
RATE_LIMIT_ENABLED=false
```

---

## 引擎问题

### ❌ Edge TTS 合成失败

**症状：**
```
Failed to load Edge TTS voices: 'LocalName'
```

**解决方案：**
```bash
# 更新 edge-tts
uv pip install --upgrade edge-tts

# 清除缓存
rm -rf ~/.cache/edge-tts/

# 检查网络连接（Edge TTS 需要联网）
curl -I https://speech.platform.bing.com
```

### ❌ OpenAI TTS API 密钥错误

**症状：**
```
Invalid API key
```

**解决方案：**
```bash
# 检查 .env 配置
grep OPENAI .env

# 正确格式
OPENAI_TTS_ENABLED=true
OPENAI_API_KEY=sk-...

# 验证密钥
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### ❌ 所有引擎都失败

**症状：**
```
All engines failed. Tried: ['openai', 'edge', 'pyttsx3']
```

**诊断步骤：**

1. **检查引擎状态**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **检查熔断器状态**
   ```bash
   curl http://localhost:8000/api/v1/tts/circuit-breaker/status
   ```

3. **重置熔断器**
   ```bash
   curl -X POST http://localhost:8000/api/v1/tts/circuit-breaker/reset/edge
   ```

4. **测试离线引擎**
   ```json
   {
     "text": "Test",
     "engine": "pyttsx3",
     "voice": "default"
   }
   ```

### ❌ Pyttsx3 引擎不可用

**症状：**
```
pyttsx3 engine not available
```

**解决方案：**

**Windows:**
```powershell
# 检查 pywin32
uv pip install --upgrade pywin32

# 运行 pywin32 后安装脚本
python Scripts/pywin32_postinstall.py -install
```

**Linux:**
```bash
# 安装 espeak
sudo apt-get install espeak espeak-data libespeak-dev
# 或
sudo yum install espeak

# 重启应用
```

**macOS:**
```bash
# macOS 自带语音支持，检查权限
# 系统偏好设置 > 安全性与隐私 > 辅助功能
```

---

## 数据库问题

### ❌ 数据库锁定

**症状：**
```
sqlite3.OperationalError: database is locked
```

**解决方案：**
```bash
# 方法 1: 关闭其他连接
# 停止所有 TTS System 实例

# 方法 2: 重启应用
make run

# 方法 3: 清理锁文件
rm database/*.db-journal

# 方法 4: 切换到 PostgreSQL（生产环境推荐）
```

### ❌ 迁移失败

**症状：**
```
alembic.util.exc.CommandError: Can't locate revision
```

**解决方案：**
```bash
# 查看当前版本
uv run alembic current

# 查看迁移历史
uv run alembic history

# 强制重置到最新
uv run alembic stamp head
uv run alembic upgrade head

# 如果完全损坏，重新初始化
rm database/*.db
rm -rf migrations/versions/*.py
uv run alembic upgrade head
```

---

## 性能问题

### ⚠️ 响应速度慢

**诊断步骤：**

1. **检查缓存**
   ```bash
   curl http://localhost:8000/api/v1/tts/cache/stats
   ```

2. **启用缓存**
   ```bash
   # .env
   CACHE_ENABLED=true
   CACHE_TTL_DAYS=30
   ```

3. **查看处理时间**
   ```json
   {
     "processing_time_ms": 342.5,  // 如果 >1000ms 需要优化
     "cached": false
   }
   ```

4. **使用快速引擎**
   - Edge TTS: ~500ms（无缓存）
   - OpenAI: ~1000ms
   - Youdao: ~800ms
   - Pyttsx3: ~100ms（最快）

### ⚠️ 内存占用高

**解决方案：**
```bash
# 清理缓存
curl -X POST http://localhost:8000/api/v1/tts/cache/cleanup

# 减少 worker 数量
uvicorn packages.api.main:app --workers 2

# 限制缓存大小
# .env
CACHE_MAX_SIZE_MB=512
```

### ⚠️ 磁盘占用高

**解决方案：**
```bash
# 查看存储统计
ls -lh storage/cache/
du -sh storage/*

# 清理缓存
curl -X DELETE http://localhost:8000/api/v1/tts/cache/clear

# 设置自动清理
# .env
CACHE_TTL_DAYS=7
```

---

## Docker 问题

### ❌ Docker 构建失败

**症状：**
```
ERROR: failed to solve: process "/bin/sh -c uv sync" did not complete successfully
```

**解决方案：**
```bash
# 清理 Docker 缓存
docker builder prune

# 重新构建（不使用缓存）
docker build --no-cache -t tts-system:latest .

# 检查 Dockerfile
docker build -t tts-system:latest . --progress=plain
```

### ❌ 容器无法启动

**症状：**
```
Error: Container exited with code 1
```

**诊断步骤：**
```bash
# 查看日志
docker logs tts-api

# 交互式启动
docker run -it --rm tts-system:latest /bin/bash

# 检查环境变量
docker exec tts-api env
```

### ❌ 挂载卷权限问题

**症状：**
```
PermissionError: [Errno 13] Permission denied: '/app/storage/cache'
```

**解决方案：**
```bash
# Linux/macOS: 修改权限
chmod -R 755 storage/ database/

# 或在 Dockerfile 中添加
RUN chown -R appuser:appuser /app/storage /app/database
```

---

## 🔍 通用调试技巧

### 1. 启用详细日志

```bash
# .env
LOG_LEVEL=DEBUG
LOG_FORMAT=pretty

# 启动服务
make run
```

### 2. 使用健康检查

```bash
# 检查整体健康
curl http://localhost:8000/api/v1/health

# 检查引擎健康
curl http://localhost:8000/api/v1/voices

# 检查熔断器
curl http://localhost:8000/api/v1/tts/circuit-breaker/status
```

### 3. 测试最小配置

```bash
# 只启用 Edge TTS
EDGE_TTS_ENABLED=true
OPENAI_TTS_ENABLED=false
YOUDAO_TTS_ENABLED=false

# 禁用附加功能
CACHE_ENABLED=false
RATE_LIMIT_ENABLED=false
```

### 4. 使用交互式 API 文档

访问 http://localhost:8000/api/v1/docs

- 查看所有端点
- 直接测试 API
- 查看请求/响应模型

---

## 📞 获取帮助

如果以上方法都无法解决问题：

1. **查看文档**
   - [README.md](../README.md) - 项目概览
   - [API.md](API.md) - API 使用文档
   - [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南

2. **检查 Issues**
   - [GitHub Issues](https://github.com/pzone618/tts_sys/issues)
   - 搜索类似问题

3. **提交 Bug 报告**
   
   提供以下信息：
   - 操作系统和版本
   - Python 版本
   - 错误日志（完整堆栈追踪）
   - 重现步骤
   - .env 配置（移除敏感信息）

4. **常用日志位置**
   ```bash
   # 应用日志
   tail -f logs/tts_system.log

   # Docker 日志
   docker logs -f tts-api

   # 系统日志
   # Linux: /var/log/syslog
   # macOS: /var/log/system.log
   ```

---

## 🎯 快速诊断命令

```bash
# 一键诊断脚本
cat > diagnose.sh << 'EOF'
#!/bin/bash
echo "=== TTS System Diagnostics ==="

echo "\n1. Python Version:"
python --version

echo "\n2. uv Version:"
uv --version

echo "\n3. Database Status:"
ls -lh database/

echo "\n4. Storage Status:"
du -sh storage/*

echo "\n5. Service Health:"
curl -s http://localhost:8000/api/v1/health | jq

echo "\n6. Circuit Breaker Status:"
curl -s http://localhost:8000/api/v1/tts/circuit-breaker/status | jq

echo "\n7. Cache Stats:"
curl -s http://localhost:8000/api/v1/tts/cache/stats | jq

echo "\n8. Available Engines:"
curl -s http://localhost:8000/api/v1/voices | jq '[.[] | .engine] | unique'

echo "\n=== Diagnostics Complete ==="
EOF

chmod +x diagnose.sh
./diagnose.sh
```

记住：**90%的问题可以通过检查日志和 .env 配置文件解决！** 🎉
