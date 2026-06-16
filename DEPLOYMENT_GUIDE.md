# Video Processor MVP - Deployment Guide

This guide provides comprehensive instructions for deploying the Video Processor MVP to AWS, including both EC2 and ECS deployment options.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [EC2 Deployment](#ec2-deployment)
4. [ECS Deployment](#ecs-deployment)
5. [GitHub Actions CI/CD](#github-actions-cicd)
6. [Monitoring and Health Checks](#monitoring-and-health-checks)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Tools

- **AWS CLI** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Docker** (for ECS deployments) - [Installation Guide](https://docs.docker.com/get-docker/)
- **SSH Client** (for EC2 deployments)
- **Git**

### AWS Account Setup

1. **AWS Account** with appropriate permissions
2. **IAM User** with the following permissions:
   - EC2 Full Access (for EC2 deployment)
   - ECS Full Access (for ECS deployment)
   - ECR Full Access (for Docker image management)
   - VPC Read Access
   - CloudWatch Logs Access

3. **AWS Credentials** configured:
   ```bash
   aws configure
   ```

### GitHub Secrets (for CI/CD)

If using GitHub Actions, configure the following secrets in your repository:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `EC2_SSH_KEY` (base64 encoded private key)

## Quick Start

### Deploy to EC2

```bash
./deploy-ec2.sh
```

### Deploy to ECS

```bash
./deploy-aws-simple.sh
```

### Unified Deployment

```bash
# Deploy to EC2
./deploy-production.sh ec2

# Deploy to ECS
./deploy-production.sh ecs

# Deploy to both
./deploy-production.sh both
```

## EC2 Deployment

### Initial Setup

1. **Launch EC2 Instance**
   - AMI: Amazon Linux 2
   - Instance Type: t3.medium or larger
   - Security Group: Allow SSH (22) and HTTP (8000)
   - Key Pair: Create and download

2. **One-time Environment Setup**
   ```bash
   ssh -i your-key.pem ec2-user@YOUR_EC2_IP
   # On EC2:
   curl -O https://raw.githubusercontent.com/your-repo/video-processor-mvp/main/setup-ec2-env.sh
   bash setup-ec2-env.sh
   ```

3. **Deploy Application**
   ```bash
   # From your local machine:
   export EC2_IP=your-ec2-ip
   export SSH_KEY=your-key.pem
   ./deploy-ec2.sh
   ```

### Deployment Process

The `deploy-ec2.sh` script performs the following steps:

1. **Pre-flight Checks**
   - Validates SSH connectivity
   - Checks EC2 instance status
   - Verifies prerequisites

2. **Code Synchronization**
   - Syncs application code via rsync
   - Excludes unnecessary files (media, cache, etc.)

3. **Environment Setup**
   - Creates/updates Python virtual environment
   - Installs dependencies (compatible with Python 3.7+)
   - Creates SQLite3 patches for compatibility

4. **Database Migrations**
   - Runs Django migrations
   - Collects static files

5. **Application Startup**
   - Starts Gunicorn server
   - Verifies health endpoints

6. **Health Verification**
   - Checks `/login/` endpoint
   - Validates HTTP response codes

### Manual Startup

If you need to start the application manually:

```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
cd ~/app
bash startup-ec2.sh
```

### Systemd Service

The application can run as a systemd service for auto-restart:

```bash
# Enable service
sudo systemctl enable video-processor

# Start service
sudo systemctl start video-processor

# Check status
sudo systemctl status video-processor

# View logs
sudo journalctl -u video-processor -f
```

## ECS Deployment

### Prerequisites

- Docker installed locally
- ECR repository created (or will be created automatically)
- ECS cluster and service configured

### Deployment Process

The `deploy-aws-simple.sh` script performs the following:

1. **Infrastructure Setup**
   - Creates ECS cluster (if needed)
   - Sets up VPC and networking
   - Creates security groups
   - Configures load balancer

2. **Docker Image**
   - Builds production Docker image
   - Pushes to ECR
   - Tags with latest and commit SHA

3. **Task Definition**
   - Creates/updates ECS task definition
   - Configures health checks
   - Sets environment variables

4. **Service Deployment**
   - Creates/updates ECS service
   - Configures load balancer integration
   - Waits for service stabilization

### Manual ECS Deployment

```bash
# Build and push image
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-2.amazonaws.com
docker build -f Dockerfile.prod -t video-processor-mvp:latest .
docker tag video-processor-mvp:latest YOUR_ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/video-processor-mvp:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/video-processor-mvp:latest

# Deploy
./deploy-aws-simple.sh
```

## GitHub Actions CI/CD

### Workflow Overview

The repository includes three GitHub Actions workflows:

1. **Test Workflow** (`.github/workflows/test.yml`)
   - Runs on push to `main` or `develop`
   - Runs on pull requests
   - Executes Django tests
   - Performs code quality checks

2. **EC2 Deployment** (`.github/workflows/deploy-ec2.yml`)
   - Triggers on push to `main`
   - Can be manually triggered
   - Deploys to EC2 instance
   - Verifies deployment health

3. **ECS Deployment** (`.github/workflows/deploy-ecs.yml`)
   - Triggers on push to `production` branch
   - Can be manually triggered
   - Builds and pushes Docker image
   - Deploys to ECS Fargate

### Setting Up GitHub Actions

1. **Configure Secrets**
   - Go to repository Settings → Secrets → Actions
   - Add the following secrets:
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`
     - `EC2_SSH_KEY` (base64 encoded private key)

2. **Workflow Triggers**
   - **Test**: Automatically on push/PR
   - **EC2 Deploy**: Push to `main` or manual trigger
   - **ECS Deploy**: Push to `production` or manual trigger

### Manual Workflow Trigger

```bash
# Trigger EC2 deployment
gh workflow run deploy-ec2.yml -f ec2_ip=18.220.86.138

# Trigger ECS deployment
gh workflow run deploy-ecs.yml
```

## Monitoring and Health Checks

### Health Check Script

Run the health check script to monitor application status:

```bash
# On EC2
bash ~/app/health-check.sh

# From local machine
ssh -i your-key.pem ec2-user@YOUR_EC2_IP 'bash ~/app/health-check.sh'
```

### Deployment Status Dashboard

View comprehensive deployment status:

```bash
./deployment-status.sh
```

This script shows:
- EC2 instance status and application health
- ECS service status and task health
- Load balancer target health
- Quick access URLs

### CloudWatch Logs (ECS)

View ECS container logs:

```bash
aws logs tail /ecs/video-processor --follow --region us-east-2
```

### Application Logs (EC2)

```bash
# Gunicorn access logs
tail -f ~/app/logs/gunicorn-access.log

# Gunicorn error logs
tail -f ~/app/logs/gunicorn-error.log

# Systemd service logs
sudo journalctl -u video-processor -f
```

## Troubleshooting

### EC2 Deployment Issues

**Problem: Application not starting**
```bash
# Check Gunicorn process
ps aux | grep gunicorn

# Check logs
tail -50 ~/app/logs/gunicorn-error.log

# Check port
netstat -tln | grep 8000

# Restart manually
cd ~/app && bash startup-ec2.sh
```

**Problem: SQLite version error**
- The deployment script automatically patches SQLite3 using `pysqlite3-binary`
- Ensure `wsgi_patched.py` and `manage_patched.py` are present

**Problem: Dependencies not installing**
- Check Python version: `python3 --version`
- Ensure virtual environment is activated
- Check disk space: `df -h`

### ECS Deployment Issues

**Problem: Tasks not starting**
```bash
# Check task status
aws ecs describe-tasks \
  --cluster video-processor-cluster \
  --tasks TASK_ID \
  --region us-east-2

# Check CloudWatch logs
aws logs tail /ecs/video-processor --follow --region us-east-2
```

**Problem: Health check failures**
- Verify health endpoint: `/api/health/`
- Check health check configuration in task definition
- Increase `startPeriod` if application takes time to start

**Problem: Out of memory**
- Increase task memory in task definition (currently 4096 MB)
- Check application memory usage
- Consider optimizing Docker image

### Common Issues

**Port 8000 not accessible**
- Check security group rules
- Verify EC2 instance is running
- Check firewall settings

**Database connection errors**
- Verify database configuration
- Check security group rules (for RDS)
- Ensure database is accessible from instance

## Rollback Procedures

### EC2 Rollback

1. **Stop current application**
   ```bash
   ssh -i your-key.pem ec2-user@YOUR_EC2_IP
   pkill -f gunicorn
   ```

2. **Restore previous version**
   ```bash
   cd ~/app
   git checkout PREVIOUS_COMMIT
   bash startup-ec2.sh
   ```

### ECS Rollback

1. **Revert to previous task definition**
   ```bash
   aws ecs update-service \
     --cluster video-processor-cluster \
     --service video-processor-service \
     --task-definition video-processor-task:PREVIOUS_REVISION \
     --force-new-deployment \
     --region us-east-2
   ```

2. **Or use previous Docker image**
   ```bash
   # Update task definition to use previous image tag
   # Then update service
   ```

## Best Practices

1. **Always test deployments in staging first**
2. **Use health checks to verify deployments**
3. **Monitor logs after deployment**
4. **Keep deployment scripts in version control**
5. **Use environment-specific configurations**
6. **Implement proper backup strategies**
7. **Set up CloudWatch alarms for critical metrics**

## Support

For issues or questions:
- Check logs first
- Review this deployment guide
- Check AWS Console for resource status
- Review GitHub Actions workflow runs

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

