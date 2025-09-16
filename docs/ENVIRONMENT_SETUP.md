# Environment Configuration Guide

This guide explains how to set up and manage environment variables for the Minca AI MVP underwriting project.

## 📁 Environment File Structure

The project uses an organized environment structure with separation between environments and services:

```
configs/env/
├── .env.development     # Local development (default)
├── .env.staging         # Staging environment
├── .env.production      # Production environment
├── .env.example         # Template for all environments
└── service-specific/
    ├── .env.api
    ├── .env.document-processor
    ├── .env.vehicle-codifier
    ├── .env.smart-intake
    └── .env.ui
```

## 🚀 Quick Setup

### For Development (Default)

1. **Copy the development environment file:**
   ```bash
   cp configs/env/.env.example configs/env/.env.development
   ```

2. **Edit the development file with your values:**
   ```bash
   # Edit configs/env/.env.development
   # Most default values work for local development
   # Only change OPENAI_API_KEY if you need vehicle codification
   ```

3. **Start the services:**
   ```bash
   docker compose up -d
   ```

### For Staging/Production

1. **Copy and customize environment files:**
   ```bash
   # For staging
   cp configs/env/.env.example configs/env/.env.staging
   # Edit configs/env/.env.staging with staging-specific values
   
   # For production
   cp configs/env/.env.example configs/env/.env.production
   # Edit configs/env/.env.production with production values
   ```

2. **Update docker-compose.yml to use the appropriate environment:**
   ```yaml
   # Change all services from:
   env_file:
     - configs/env/.env.development
   # To:
   env_file:
     - configs/env/.env.staging  # or .env.production
   ```

## 📋 Environment Variables Reference

### Core Infrastructure (`configs/env/.env.{environment}`)

| Variable | Description | Development | Staging/Production |
|----------|-------------|-------------|-------------------|
| `NODE_ENV` | Node.js environment | `development` | `production` |
| `ENVIRONMENT` | App environment | `development` | `staging`/`production` |
| `LOG_LEVEL` | Logging level | `DEBUG` | `INFO`/`WARNING` |

### Database Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `minca` |
| `POSTGRES_USER` | Database user | `minca` |
| `POSTGRES_PASSWORD` | Database password | `your_password` |
| `DATABASE_URL` | Full connection string | `postgresql+psycopg://user:pass@host:5432/db` |

### Storage Configuration

| Variable | Description | Development | Production |
|----------|-------------|-------------|------------|
| `S3_ENDPOINT_URL` | Storage endpoint | `http://minio:9000` | `https://s3.amazonaws.com` |
| `S3_BUCKET_RAW` | Raw files bucket | `raw` | `minca-prod-raw` |
| `S3_BUCKET_EXPORTS` | Export files bucket | `exports` | `minca-prod-exports` |
| `AWS_ACCESS_KEY_ID` | AWS access key | MinIO user | AWS key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | MinIO password | AWS secret |

### Service-Specific Variables

#### API Service (`configs/env/service-specific/.env.api`)
- `API_HOST`, `API_PORT`: Server configuration
- `CORS_ORIGINS`: Allowed origins for CORS
- `RATE_LIMIT_*`: Rate limiting settings
- `ENABLE_*`: Feature flags

#### Document Processor (`configs/env/service-specific/.env.document-processor`)
- `MAX_FILE_SIZE`: Maximum upload size
- `ALLOWED_FILE_TYPES`: Supported file formats
- `PROCESSING_TIMEOUT`: Processing time limit
- `BATCH_SIZE`: Processing batch size

#### Vehicle Codifier (`configs/env/service-specific/.env.vehicle-codifier`)
- `OPENAI_API_KEY`: OpenAI API key for embeddings
- Vehicle catalog data managed via S3 + Postgres (no local dataset paths)
- `CONFIDENCE_THRESHOLD_*`: ML confidence thresholds
- `EMBEDDING_MODEL`: ML model configuration

#### Smart Intake (`configs/env/service-specific/.env.smart-intake`)
- `AZURE_*`: Azure/Outlook integration
- `EMAIL_*`: Email processing settings
- `WEBHOOK_*`: Webhook configuration

#### UI (`configs/env/service-specific/.env.ui`)
- `NEXT_PUBLIC_*`: Public environment variables for Next.js
- `NEXT_PUBLIC_API_URL`: API endpoint URLs
- Feature flags and UI configuration

## 🔧 Environment Management

### Switching Environments

To switch between environments, update the `env_file` entries in `docker-compose.yml`:

```yaml
# Development (default)
env_file:
  - configs/env/.env.development
  - configs/env/service-specific/.env.{service}

# Staging
env_file:
  - configs/env/.env.staging
  - configs/env/service-specific/.env.{service}

# Production
env_file:
  - configs/env/.env.production
  - configs/env/service-specific/.env.{service}
```

### Environment Variable Precedence

Docker Compose loads environment variables in this order (highest to lowest priority):

1. `environment:` section in docker-compose.yml
2. Service-specific env files (`configs/env/service-specific/.env.{service}`)
3. Main environment file (`configs/env/.env.{environment}`)
4. Shell environment variables

### Local Overrides

For local development overrides, you can still use a root `.env` file:

```bash
# Create a local override file
echo "OPENAI_API_KEY=your_local_key" > .env
```

This will override values from the organized environment files.

## 🔒 Security Best Practices

### Development
- Use placeholder values in `.env.example`
- Keep real API keys in your local environment files
- Never commit actual environment files to git

### Staging/Production
- Use strong, unique passwords
- Store sensitive values in secure secret management systems
- Rotate API keys and passwords regularly
- Use environment-specific AWS accounts and resources

### Git Configuration

The `.gitignore` file is configured to:
- ✅ Allow: `configs/env/.env.example`
- ❌ Block: All other environment files in `configs/env/`

## 🐛 Troubleshooting

### Environment Variables Not Loading

#### For Docker Services
1. **Check file paths in docker-compose.yml:**
   ```bash
   # Verify files exist
   ls -la configs/env/
   ls -la configs/env/service-specific/
   ```

2. **Check Docker Compose syntax:**
   ```bash
   docker compose config
   ```

3. **Verify environment variables in container:**
   ```bash
   docker compose exec api env | grep -E "(DATABASE|S3|OPENAI)"
   ```

#### For Services Running Outside Docker
If you're running services directly (e.g., `poetry run uvicorn src.api.main:app`), environment loading uses dynamic path resolution:

1. **Check startup logs for environment loading:**
   ```bash
   # You should see output like:
   Loading environment from: /path/to/MVP_underwriting/configs/env/.env.development
   ✅ Loaded .env.development
   Loading API config from: /path/to/MVP_underwriting/configs/env/service-specific/.env.api
   ✅ Loaded .env.api
   ```

2. **If you see path errors:**
   ```bash
   # Check if files exist at the reported paths
   ls -la /path/shown/in/error/.env.development
   
   # Verify you're running from the correct directory
   pwd  # Should be in services/{service-name}
   ```

3. **Debug environment loading:**
   ```python
   # Add to your service's main.py for debugging
   import pathlib
   project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
   print(f"Project root: {project_root}")
   print(f"Environment dir: {project_root / 'configs' / 'env'}")
   ```

4. **Common path resolution issues:**
   - **Wrong working directory**: Ensure you're running from `services/{service-name}/`
   - **Symlinks**: Path resolution may fail with complex symlink setups
   - **File permissions**: Ensure environment files are readable

#### Environment Loading Best Practices
- Services automatically detect and load both base and service-specific environment files
- Path resolution is dynamic and works from any service directory
- Startup logs show exactly which files are being loaded
- Missing files are reported with full paths for easy debugging

### Service-Specific Issues

1. **API service not starting:**
   - Check `configs/env/service-specific/.env.api`
   - Verify database connection in `configs/env/.env.development`

2. **Vehicle codifier failing:**
   - Ensure `OPENAI_API_KEY` is set in `configs/env/service-specific/.env.vehicle-codifier`
   - Check dataset path configuration

3. **UI not connecting to APIs:**
   - Verify `NEXT_PUBLIC_*` variables in `configs/env/service-specific/.env.ui`
   - Check that API services are running

### Migration from Old Structure

If you have an existing `.env` file in the root:

1. **Backup your current file:**
   ```bash
   cp .env .env.backup
   ```

2. **Split variables into appropriate files:**
   - Database/storage → `configs/env/.env.development`
   - Service-specific → `configs/env/service-specific/.env.{service}`

3. **Test the new configuration:**
   ```bash
   docker compose down
   docker compose up -d
   ```

## 📚 Additional Resources

- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)

---

For questions or issues with environment configuration, please check the troubleshooting section above or create an issue in the project repository.
