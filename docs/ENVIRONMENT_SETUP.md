# Environment Configuration Guide

This guide explains how to set up and manage environment variables for the Minca AI MVP underwriting project.

## 📁 Environment File Structure

The project uses a simple, clean environment structure:

```
configs/env/
├── .env.development     # Local development (default)
├── .env.staging         # Staging environment  
├── .env.production      # Production environment
└── .env.example         # Template for all environments
```

## 🚀 Quick Setup

### For Development (Default)

1. **Copy the example environment file:**
   ```bash
   cp configs/env/.env.example configs/env/.env.development
   ```

2. **Edit the development file with your values:**
   ```bash
   # Edit configs/env/.env.development
   # Required changes:
   # - DATABASE_URL: Your PostgreSQL connection string
   # - AWS credentials: Your AWS S3 credentials
   # - OPENAI_API_KEY: Your OpenAI API key (for vehicle codification)
   # - S3_BUCKET_NAME: Your S3 bucket name
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

### Database Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Full PostgreSQL connection string | `postgresql+psycopg://user:pass@host:5432/db?sslmode=require` |

### AWS S3 Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_DEFAULT_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET_RAW` | Raw files bucket | `raw` |
| `S3_BUCKET_EXPORTS` | Export files bucket | `exports` |
| `S3_BUCKET_NAME` | Main bucket name | `minca-underwriting` |

### Queue Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `QUEUE_BACKEND` | Queue backend type | `local` |

### OpenAI Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | `sk-proj-...` |
| `OPENAI_MODEL` | Model to use | `gpt-4o-mini` |
| `OPENAI_MAX_TOKENS` | Max tokens per request | `1000` |
| `OPENAI_TEMPERATURE` | Model temperature | `0.1` |

### Embedding Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `EMBEDDING_MODEL` | Embedding model name | `intfloat/multilingual-e5-large` |
| `EMBEDDING_DIMENSION` | Vector dimensions | `1024` |
| `SIMILARITY_THRESHOLD` | Similarity matching threshold | `0.70` |
| `FUZZY_MATCH_THRESHOLD` | Fuzzy matching threshold | `0.80` |
| `W_EMBED` | Embedding weight | `0.7` |
| `W_FUZZY` | Fuzzy matching weight | `0.3` |

### API Service Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000,http://localhost:8000` |

### Service URLs Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `VEHICLE_CODIFIER_HOST` | Vehicle codifier host | `0.0.0.0` |
| `VEHICLE_CODIFIER_PORT` | Vehicle codifier port | `8002` |
| `SMART_INTAKE_HOST` | Smart intake host | `0.0.0.0` |
| `SMART_INTAKE_PORT` | Smart intake port | `8003` |

### Azure Configuration (Smart Intake Service)

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_TENANT_ID` | Azure tenant ID | `your-tenant-id` |
| `AZURE_CLIENT_ID` | Azure client ID | `your-client-id` |
| `AZURE_CLIENT_SECRET` | Azure client secret | `your-client-secret` |

### AMIS Catalog Configuration

The AMIS vehicle catalog is managed through database and S3 storage:
- **Database**: Vehicle data stored in `amis_catalog` table with embeddings
- **Tools**: Use `upload_amis_standalone.py` and `fix_embeddings_standalone.py` for catalog management
- **Status**: Catalog versions tracked in `catalog_import` table with LOADED/EMBEDDED/ACTIVE status

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
2. Environment file specified in docker-compose.yml (`configs/env/.env.{environment}`)
3. Shell environment variables

### Local Overrides

For local development overrides, you can create a root `.env` file:

```bash
# Create a local override file (optional)
echo "OPENAI_API_KEY=your_local_key" > .env
```

However, it's recommended to directly edit `configs/env/.env.development` for consistency.

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
