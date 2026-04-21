# 部署指南

## 方式 1: 本地部署

### 前提条件

- Python 3.13+
- uv 包管理器

### 步骤

1. **克隆仓库**
   ```bash
   git clone <your-repo-url>
   cd tts_sys
   ```

2. **安装依赖**
   ```bash
   uv sync
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，添加你的 API Keys
   # 可选：修改 API_PORT（默认：8000）
   ```

4. **初始化数据库**
   ```bash
   uv run alembic upgrade head
   ```

5. **启动服务**
   ```bash
   # 开发模式（自动重载，使用 .env 中的 API_PORT）
   make run
   # 或手动指定
   uv run uvicorn packages.api.main:app --reload --host 0.0.0.0 --port ${API_PORT:-8000}

   # 生产模式（多 worker）
   make prod
   # 或手动指定
   uv run uvicorn packages.api.main:app --host 0.0.0.0 --port ${API_PORT:-8000} --workers 4
   ```

6. **快速启动脚本**
   ```bash
   python scripts/quickstart.py
   ```

## 方式 2: Docker 部署

### 使用 Docker

```bash
# 构建镜像
docker build -t tts-system .

# 运行容器（默认端口 8000，可通过 API_PORT 修改）
docker run -d \
  --name tts-api \
  -p 8000:8000 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/database:/app/database \
  -e API_PORT=8000 \
  -e OPENAI_API_KEY=your_key \
  tts-system

# 使用自定义端口（例如 3000）
docker run -d \
  --name tts-api \
  -p 3000:3000 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/database:/app/database \
  -e API_PORT=3000 \
  tts-system
```

### 使用 Docker Compose

在启动前，可在 `.env` 文件中设置 `API_PORT`：

```bash
# .env 文件
API_PORT=8000  # 或您需要的任何端口

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 方式 3: 云平台部署

### Azure App Service

1. **创建 App Service**
   ```bash
   az webapp create \
     --name tts-system-api \
     --resource-group myResourceGroup \
     --plan myAppServicePlan \
     --runtime "PYTHON:3.13"
   ```

2. **配置环境变量**
   ```bash
   az webapp config appsettings set \
     --name tts-system-api \
     --resource-group myResourceGroup \
     --settings \
       OPENAI_API_KEY=your_key \
       DATABASE_URL=sqlite:///home/site/wwwroot/database/tts_sys.db
   ```

3. **部署代码**
   ```bash
   az webapp up \
     --name tts-system-api \
     --resource-group myResourceGroup
   ```

### AWS ECS

1. **构建并推送镜像**
   ```bash
   # 登录 ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

   # 构建镜像
   docker build -t tts-system .

   # 标记镜像
   docker tag tts-system:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/tts-system:latest

   # 推送镜像
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/tts-system:latest
   ```

2. **创建 ECS 任务定义和服务**
   - 使用 AWS Console 或 CloudFormation
   - 配置环境变量
   - 设置负载均衡器

### Google Cloud Run

```bash
# 构建镜像
gcloud builds submit --tag gcr.io/PROJECT_ID/tts-system

# 部署到 Cloud Run
gcloud run deploy tts-system \
  --image gcr.io/PROJECT_ID/tts-system \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your_key
```

## 生产环境配置

### 1. 使用 PostgreSQL（推荐）

```bash
# 安装 PostgreSQL 驱动
uv add psycopg2-binary

# 更新 .env
DATABASE_URL=postgresql://user:password@localhost/tts_sys
```

### 2. 使用 Redis 缓存

```bash
# 安装 Redis 客户端
uv add redis

# 更新配置（future feature）
REDIS_URL=redis://localhost:6379/0
```

### 3. 配置反向代理 (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件缓存
    location /api/v1/audio/ {
        proxy_pass http://localhost:8000;
        proxy_cache_valid 200 1d;
        add_header Cache-Control "public, max-age=86400";
    }
}
```

### 4. 使用 Supervisor 管理进程

```ini
[program:tts-api]
command=/path/to/.venv/bin/uvicorn packages.api.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/path/to/tts_sys
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tts-api.log
```

### 5. 配置 Systemd Service

```ini
[Unit]
Description=TTS System API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/tts_sys
Environment="PATH=/path/to/.venv/bin"
ExecStart=/path/to/.venv/bin/uvicorn packages.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable tts-api
sudo systemctl start tts-api
sudo systemctl status tts-api
```

## 监控和日志

### 1. 健康检查端点

```bash
curl http://localhost:8000/api/v1/health
```

### 2. 日志配置

编辑 `.env`：
```env
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3. 集成监控工具

#### Prometheus + Grafana

```python
# 添加到 requirements
# prometheus-fastapi-instrumentator

# 在 main.py 中添加
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

#### Sentry 错误追踪

```python
# 安装 sentry-sdk
# 在 main.py 中添加
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

## 性能优化

### 1. 数据库连接池

```python
# 在 database.py 中配置
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)
```

### 2. 启用 Gzip 压缩

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 3. 负载均衡

使用 Nginx 或云平台负载均衡器：
```nginx
upstream tts_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    location / {
        proxy_pass http://tts_backend;
    }
}
```

## 安全建议

1. **使用 HTTPS**
   - 配置 SSL/TLS 证书
   - 使用 Let's Encrypt 免费证书

2. **API Key 认证**
   ```python
   # 添加 API Key 中间件
   from fastapi import Security, HTTPException
   from fastapi.security import APIKeyHeader
   
   api_key_header = APIKeyHeader(name="X-API-Key")
   
   async def verify_api_key(api_key: str = Security(api_key_header)):
       if api_key != settings.api_key:
           raise HTTPException(status_code=403)
   ```

3. **速率限制**
   - 使用 slowapi 或云平台的 API Gateway

4. **输入验证**
   - 已通过 Pydantic 实现
   - 添加额外的业务逻辑验证

5. **定期更新依赖**
   ```bash
   uv sync --upgrade
   ```

## 故障排查

### 数据库连接失败
```bash
# 检查数据库文件权限
ls -l database/

# 重新初始化
rm database/tts_sys.db
uv run alembic upgrade head
```

### 端口被占用
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

### 内存泄漏
```bash
# 监控内存使用
docker stats tts-api

# 重启服务
docker-compose restart
```

## 备份和恢复

### 备份数据库
```bash
# SQLite
cp database/tts_sys.db database/tts_sys.db.backup

# PostgreSQL
pg_dump -U user -d tts_sys > backup.sql
```

### 备份音频缓存
```bash
tar -czf storage_backup.tar.gz storage/
```

## 扩展阅读

- [FastAPI 部署文档](https://fastapi.tiangolo.com/deployment/)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [云平台部署指南](https://docs.microsoft.com/azure/app-service/)
