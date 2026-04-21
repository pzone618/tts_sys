# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of TTS System seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Reporting Process

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via:

1. **Email**: Send details to [your-security-email@example.com]
2. **Private Disclosure**: Use GitHub's private vulnerability reporting feature

### What to Include

Please include the following information in your report:

- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: 7 days, High: 30 days, Medium: 60 days)

## Security Best Practices

### API Keys Management

**Never commit sensitive credentials to the repository:**

```bash
# Use environment variables
export OPENAI_API_KEY="your-key-here"
export YOUDAO_APP_KEY="your-key-here"
```

**Use `.env` file (add to .gitignore):**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### Database Security

1. **Use SQLite with Proper Permissions**
   ```bash
   chmod 600 database/tts_sys.db
   ```

2. **Regular Backups**
   ```bash
   # Backup database regularly
   cp database/tts_sys.db database/backups/tts_sys_$(date +%Y%m%d).db
   ```

3. **Migrate to PostgreSQL for Production**
   - SQLite is suitable for development
   - Use PostgreSQL/MySQL for production deployments

### API Security

1. **Enable Rate Limiting**
   ```env
   RATE_LIMIT_ENABLED=true
   RATE_LIMIT_PER_MINUTE=60
   ```

2. **Configure CORS Properly**
   ```env
   CORS_ORIGINS=["https://yourdomain.com"]
   CORS_ALLOW_CREDENTIALS=true
   ```

3. **Use HTTPS in Production**
   - Never deploy without TLS/SSL
   - Use reverse proxy (nginx, Caddy)
   - Consider API Gateway

4. **Input Validation**
   - All inputs are validated using Pydantic models
   - Max text length enforced (default: 5000 chars)
   - File size limits on audio outputs

### Docker Security

1. **Run as Non-Root User**
   ```dockerfile
   RUN adduser --disabled-password --gecos '' appuser
   USER appuser
   ```

2. **Scan Images Regularly**
   ```bash
   docker scan tts-system:latest
   ```

3. **Use Specific Base Image Tags**
   ```dockerfile
   FROM python:3.13.8-slim
   # Not: FROM python:3-slim
   ```

### Network Security

1. **Isolate TTS Engines**
   - Use separate API keys for each service
   - Implement circuit breakers (already included)

2. **Monitor Engine Health**
   ```bash
   curl http://localhost:8000/api/v1/tts/circuit-breaker/status
   ```

3. **Log Security Events**
   - All authentication failures
   - Rate limit violations
   - Circuit breaker state changes

### Dependency Security

1. **Regular Updates**
   ```bash
   # Check for vulnerabilities
   uv sync
   pip-audit
   ```

2. **Pin Dependencies**
   - Already configured in `pyproject.toml`
   - Review `uv.lock` before updates

3. **Audit Third-Party Packages**
   ```bash
   # Check package security
   safety check
   ```

## Known Security Considerations

### 1. API Keys in Logs

- Logs are sanitized (API keys masked)
- Configure `LOG_LEVEL=WARNING` in production
- Rotate logs regularly

### 2. Audio File Storage

- Temporary files cleaned automatically
- Cache has TTL (default: 30 days)
- Storage path permissions restricted

### 3. Circuit Breaker State

- Circuit breaker prevents DOS on failing engines
- Manual reset available via API
- Monitor circuit breaker metrics

### 4. External API Calls

- All external calls timeout after 30s
- Retry logic prevents cascading failures
- Fallback to offline engines available

## Security Checklist for Deployment

- [ ] API keys stored in environment variables
- [ ] `.env` file added to `.gitignore`
- [ ] HTTPS/TLS configured
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Database permissions set correctly
- [ ] Regular backups configured
- [ ] Logs sanitized and rotated
- [ ] Docker container runs as non-root
- [ ] Dependencies up to date
- [ ] Security headers configured (via reverse proxy)
- [ ] Monitoring and alerting set up

## Contact

For security-related questions or concerns, please contact:
- **Email**: [your-security-email@example.com]
- **Maintainer**: [@your-github-username]

## Disclosure Policy

We follow a coordinated disclosure process:

1. Security researcher reports vulnerability privately
2. We confirm and analyze the vulnerability
3. We develop and test a fix
4. We release the fix in a new version
5. We publicly disclose the vulnerability details

**Timeline**: 90 days from initial report to public disclosure (unless mutually agreed otherwise)

## Acknowledgments

We appreciate the security research community's efforts to responsibly disclose vulnerabilities. Security researchers who report valid vulnerabilities will be acknowledged in our release notes (unless they prefer to remain anonymous).
