#!/bin/bash

# RDS PostgreSQL Setup Script for Video Processor MVP
# This script creates an RDS PostgreSQL instance for production use

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-2}"
DB_INSTANCE_IDENTIFIER="${DB_INSTANCE_IDENTIFIER:-video-processor-db}"
DB_NAME="${DB_NAME:-video_recall_db}"
DB_USERNAME="${DB_USERNAME:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_INSTANCE_CLASS="${DB_INSTANCE_CLASS:-db.t3.medium}"
ALLOCATED_STORAGE="${ALLOCATED_STORAGE:-100}"
ENGINE_VERSION="${ENGINE_VERSION:-15.4}"

# Get VPC and security group information
echo "🔍 Getting VPC and subnet information..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)
SUBNET_GROUP_NAME="${DB_INSTANCE_IDENTIFIER}-subnet-group"

# Check if DB instance already exists
if aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_IDENTIFIER --region $AWS_REGION &>/dev/null; then
    echo "✅ RDS instance already exists: $DB_INSTANCE_IDENTIFIER"
    DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text \
        --region $AWS_REGION)
    echo "   Endpoint: $DB_ENDPOINT"
    exit 0
fi

# Generate password if not provided
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo "🔑 Generated database password (save this securely!): $DB_PASSWORD"
fi

# Create DB subnet group
echo "📦 Creating DB subnet group..."
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text --region $AWS_REGION)
SUBNET_1=$(echo $SUBNET_IDS | cut -d' ' -f1)
SUBNET_2=$(echo $SUBNET_IDS | cut -d' ' -f2)

if aws rds describe-db-subnet-groups --db-subnet-group-name $SUBNET_GROUP_NAME --region $AWS_REGION &>/dev/null; then
    echo "✅ DB subnet group already exists"
else
    aws rds create-db-subnet-group \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --db-subnet-group-description "Subnet group for Video Processor RDS" \
        --subnet-ids $SUBNET_1 $SUBNET_2 \
        --region $AWS_REGION
    echo "✅ DB subnet group created"
fi

# Get or create security group for RDS
echo "🔒 Setting up security group..."
RDS_SG_NAME="video-processor-rds-sg"
RDS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$RDS_SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$RDS_SG_ID" = "None" ] || [ -z "$RDS_SG_ID" ]; then
    RDS_SG_ID=$(aws ec2 create-security-group \
        --group-name $RDS_SG_NAME \
        --description "Security group for Video Processor RDS" \
        --vpc-id $VPC_ID \
        --query 'GroupId' \
        --output text \
        --region $AWS_REGION)
    
    # Get ECS security group to allow access
    ECS_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=video-processor-sg" \
        --query 'SecurityGroups[0].GroupId' \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "")
    
    if [ -n "$ECS_SG_ID" ] && [ "$ECS_SG_ID" != "None" ]; then
        # Allow ECS tasks to access RDS
        aws ec2 authorize-security-group-ingress \
            --group-id $RDS_SG_ID \
            --protocol tcp \
            --port 5432 \
            --source-group $ECS_SG_ID \
            --region $AWS_REGION 2>/dev/null || true
        echo "✅ Allowed ECS security group access to RDS"
    fi
    
    echo "✅ Security group created: $RDS_SG_ID"
else
    echo "✅ Security group already exists: $RDS_SG_ID"
fi

# Create RDS instance
echo "🚀 Creating RDS PostgreSQL instance..."
echo "   Instance ID: $DB_INSTANCE_IDENTIFIER"
echo "   Instance Class: $DB_INSTANCE_CLASS"
echo "   Storage: ${ALLOCATED_STORAGE}GB"
echo "   Engine Version: $ENGINE_VERSION"

aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --db-instance-class $DB_INSTANCE_CLASS \
    --engine postgres \
    --engine-version $ENGINE_VERSION \
    --allocated-storage $ALLOCATED_STORAGE \
    --storage-type gp2 \
    --db-name $DB_NAME \
    --master-username $DB_USERNAME \
    --master-user-password "$DB_PASSWORD" \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name $SUBNET_GROUP_NAME \
    --backup-retention-period 7 \
    --storage-encrypted \
    --no-publicly-accessible \
    --region $AWS_REGION \
    --no-multi-az

echo "✅ RDS instance creation initiated"
echo ""
echo "⏳ Waiting for RDS instance to be available (this may take 5-10 minutes)..."
aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --region $AWS_REGION

# Get endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text \
    --region $AWS_REGION)

echo ""
echo "🎉 RDS instance is ready!"
echo ""
echo "📊 Database Information:"
echo "   Instance ID: $DB_INSTANCE_IDENTIFIER"
echo "   Endpoint: $DB_ENDPOINT"
echo "   Port: 5432"
echo "   Database: $DB_NAME"
echo "   Username: $DB_USERNAME"
echo "   Password: $DB_PASSWORD"
echo ""
echo "🔗 Connection String:"
echo "   postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:5432/$DB_NAME"
echo ""
echo "⚠️  IMPORTANT: Save the password securely! You'll need it for DATABASE_URL."
echo ""
echo "📝 To use this database, set the DATABASE_URL environment variable:"
echo "   export DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:5432/$DB_NAME"

