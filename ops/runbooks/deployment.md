# Deployment Runbook

## Overview

This runbook covers deployment procedures for the Minca AI insurance processing platform.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed and running
- kubectl installed (if using EKS)
- Access to GitHub Container Registry

## Deployment Environments

### Development
- **URL**: http://dev.mincaai.local
- **Database**: RDS PostgreSQL (dev instance)
- **Storage**: S3 bucket `mincaai-dev-storage`
- **Monitoring**: CloudWatch (basic)

### Staging  
- **URL**: https://staging.mincaai.com
- **Database**: RDS PostgreSQL (multi-AZ)
- **Storage**: S3 bucket `mincaai-staging-storage`
- **Monitoring**: CloudWatch + custom dashboards

### Production
- **URL**: https://app.mincaai.com
- **Database**: RDS PostgreSQL (multi-AZ, backup enabled)
- **Storage**: S3 bucket `mincaai-prod-storage`
- **Monitoring**: CloudWatch + PagerDuty alerts

## Manual Deployment Process

### 1. Pre-deployment Checks

```bash
# Check current service status
aws ecs describe-services --cluster mincaai-prod --services api worker-extractor worker-codifier

# Verify database connectivity
psql $DATABASE_URL -c "SELECT 1;"

# Check S3 bucket access
aws s3 ls s3://mincaai-prod-storage/

# Verify queue availability
aws sqs get-queue-attributes --queue-url $EXTRACTOR_QUEUE_URL
```

### 2. Database Migrations

```bash
# Run pending migrations
cd apps/api
alembic upgrade head

# Verify migration success
alembic current
```

### 3. Build and Push Images

```bash
# Build all service images
services=("api" "worker-extractor" "worker-codifier" "worker-transform" "worker-exporter")

for service in "${services[@]}"; do
  echo "Building $service..."
  docker build -t ghcr.io/company/mincaai-$service:$BUILD_TAG apps/$service/
  docker push ghcr.io/company/mincaai-$service:$BUILD_TAG
done
```

### 4. Update ECS Services

```bash
# Update task definitions and deploy
for service in "${services[@]}"; do
  # Update task definition with new image
  aws ecs register-task-definition \
    --family mincaai-prod-$service \
    --task-role-arn arn:aws:iam::ACCOUNT:role/mincaai-task-role \
    --execution-role-arn arn:aws:iam::ACCOUNT:role/mincaai-execution-role \
    --container-definitions file://task-definitions/$service.json
    
  # Update service
  aws ecs update-service \
    --cluster mincaai-prod \
    --service mincaai-prod-$service \
    --force-new-deployment
done
```

### 5. Health Checks

```bash
# Wait for deployment to complete
aws ecs wait services-stable \
  --cluster mincaai-prod \
  --services mincaai-prod-api

# Check service health
curl -f https://app.mincaai.com/health
curl -f https://app.mincaai.com/api/v1/health

# Verify worker queues are processing
aws sqs get-queue-attributes \
  --queue-url $EXTRACTOR_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages
```

## Rollback Procedures

### Quick Rollback (Emergency)

```bash
# Rollback to previous task definition revision
services=("api" "worker-extractor" "worker-codifier" "worker-transform" "worker-exporter")

for service in "${services[@]}"; do
  # Get current task definition
  CURRENT_TD=$(aws ecs describe-services \
    --cluster mincaai-prod \
    --services mincaai-prod-$service \
    --query 'services[0].taskDefinition' \
    --output text)
    
  # Extract revision number and subtract 1
  FAMILY=$(echo $CURRENT_TD | cut -d':' -f1)
  REVISION=$(echo $CURRENT_TD | cut -d':' -f2)
  PREV_REVISION=$((REVISION - 1))
  
  # Rollback to previous revision
  aws ecs update-service \
    --cluster mincaai-prod \
    --service mincaai-prod-$service \
    --task-definition $FAMILY:$PREV_REVISION
done
```

### Database Rollback

```bash
# Rollback database migrations if needed
cd apps/api
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade <revision_id>
```

## Monitoring and Verification

### Service Health Endpoints

- **API**: `GET /health`
- **Workers**: Check CloudWatch logs and SQS queue metrics

### Key Metrics to Monitor

1. **API Response Times**: < 500ms p95
2. **Queue Processing**: Messages processed per minute
3. **Error Rates**: < 1% error rate
4. **Database Connections**: < 80% utilization
5. **Memory Usage**: < 80% utilization

### CloudWatch Dashboards

- **Service Overview**: Overall system health
- **API Metrics**: Response times, error rates, throughput
- **Worker Performance**: Queue depths, processing times
- **Database Performance**: Connections, query times, locks

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check task logs
aws logs describe-log-groups --log-group-name-prefix /ecs/mincaai

# Check ECS events
aws ecs describe-services --cluster mincaai-prod --services mincaai-prod-api
```

#### Database Connection Issues
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxx

# Test database connectivity
nc -zv your-db-endpoint.rds.amazonaws.com 5432
```

#### Queue Processing Stopped
```bash
# Check dead letter queues
aws sqs get-queue-attributes \
  --queue-url $EXTRACTOR_DLQ_URL \
  --attribute-names ApproximateNumberOfMessages

# Redrive messages from DLQ if needed
aws sqs purge-queue --queue-url $EXTRACTOR_DLQ_URL
```

## Post-Deployment Tasks

1. **Update monitoring alerts** for new deployment
2. **Run smoke tests** to verify functionality
3. **Check error tracking** (Sentry/CloudWatch) for new errors
4. **Update deployment documentation** with any changes
5. **Notify team** of successful deployment

## Emergency Contacts

- **On-call Engineer**: [Contact info]
- **DevOps Lead**: [Contact info]  
- **Product Owner**: [Contact info]
- **AWS Support**: [Case creation link]