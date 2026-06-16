# Terraform Infrastructure as Code

This directory contains Terraform configurations for deploying the Video Processor MVP infrastructure to AWS.

## Prerequisites

1. **Terraform installed** (>= 1.0)
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. **AWS CLI configured** with appropriate credentials
   ```bash
   aws configure
   ```

3. **AWS IAM permissions** for creating:
   - ECS clusters and services
   - ECR repositories
   - Application Load Balancers
   - RDS instances (if enabled)
   - S3 buckets
   - IAM roles and policies
   - CloudWatch log groups
   - Security groups

## Quick Start

1. **Copy example variables file:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars** with your values:
   ```bash
   # Set RDS password and other sensitive values
   vim terraform.tfvars
   ```

3. **Initialize Terraform:**
   ```bash
   terraform init
   ```

4. **Review the plan:**
   ```bash
   terraform plan
   ```

5. **Apply the configuration:**
   ```bash
   terraform apply
   ```

## What Gets Created

- **ECR Repository** - For Docker images
- **ECS Cluster** - Container orchestration
- **Application Load Balancer** - Traffic distribution
- **Target Group** - Health checks and routing
- **Security Groups** - Network security
- **CloudWatch Log Group** - Application logging
- **IAM Roles** - ECS task execution and task roles
- **S3 Bucket** - Media storage
- **RDS PostgreSQL** (optional) - Production database

## Variables

See `variables.tf` for all available variables. Key variables:

- `enable_rds` - Set to `true` to create RDS database
- `rds_password` - Database password (set via terraform.tfvars)
- `environment` - Environment name (dev, staging, production)
- `aws_region` - AWS region for deployment

## Outputs

After applying, Terraform will output:

- ECR repository URL
- ECS cluster name
- ALB DNS name
- Target group ARN
- IAM role ARNs
- S3 bucket name
- RDS endpoint (if enabled)

## Remote State (Optional)

To use remote state with S3:

1. Create an S3 bucket for Terraform state
2. Uncomment the `backend "s3"` block in `main.tf`
3. Update the bucket name and key

## Destroying Infrastructure

To destroy all created resources:

```bash
terraform destroy
```

**Warning:** This will delete all resources including databases. Make sure you have backups!

## Next Steps

After infrastructure is created:

1. Build and push Docker image to ECR
2. Create ECS task definition
3. Create ECS service
4. Set up auto-scaling (see `scripts/setup-autoscaling.sh`)
5. Set up monitoring (see `scripts/setup-monitoring.sh`)

## Notes

- The ECS task definition and service are not included in this Terraform config
- Use `deploy-aws-simple.sh` or create them manually after infrastructure is ready
- For production, enable deletion protection and use remote state
- RDS is optional - set `enable_rds = false` to use SQLite or external database

