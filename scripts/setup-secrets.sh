#!/bin/bash

# AWS Secrets Manager Setup Script for Video Processor MVP
# This script creates secrets in AWS Secrets Manager for secure credential storage

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-2}"
SECRET_NAME="${SECRET_NAME:-video-processor-secrets}"

echo "🔐 Setting up AWS Secrets Manager"
echo "=================================="

# Check if secret already exists
if aws secretsmanager describe-secret --secret-id $SECRET_NAME --region $AWS_REGION &>/dev/null; then
    echo "✅ Secret already exists: $SECRET_NAME"
    echo ""
    echo "📝 To update the secret, use:"
    echo "   aws secretsmanager update-secret --secret-id $SECRET_NAME --secret-string file://secrets.json --region $AWS_REGION"
    exit 0
fi

# Generate or prompt for secrets
echo "📋 Creating secrets..."
echo ""

# Generate SECRET_KEY if not provided
if [ -z "${SECRET_KEY:-}" ]; then
    SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    echo "🔑 Generated SECRET_KEY"
else
    echo "✅ Using provided SECRET_KEY"
fi

# Prompt for AWS credentials if not provided
if [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    read -p "Enter AWS_ACCESS_KEY_ID (or press Enter to skip): " AWS_ACCESS_KEY_ID
fi

if [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    read -sp "Enter AWS_SECRET_ACCESS_KEY (or press Enter to skip): " AWS_SECRET_ACCESS_KEY
    echo ""
fi

# Prompt for database URL if not provided
if [ -z "${DATABASE_URL:-}" ]; then
    read -p "Enter DATABASE_URL (or press Enter to skip): " DATABASE_URL
fi

# Prompt for Redis URL if not provided
if [ -z "${REDIS_URL:-}" ]; then
    read -p "Enter REDIS_URL (or press Enter to skip): " REDIS_URL
fi

# Create JSON secret
SECRET_JSON="{"

if [ -n "$SECRET_KEY" ]; then
    SECRET_JSON="$SECRET_JSON\"SECRET_KEY\":\"$SECRET_KEY\""
fi

if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    if [ "$SECRET_JSON" != "{" ]; then
        SECRET_JSON="$SECRET_JSON,"
    fi
    SECRET_JSON="$SECRET_JSON\"AWS_ACCESS_KEY_ID\":\"$AWS_ACCESS_KEY_ID\""
fi

if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    if [ "$SECRET_JSON" != "{" ]; then
        SECRET_JSON="$SECRET_JSON,"
    fi
    SECRET_JSON="$SECRET_JSON\"AWS_SECRET_ACCESS_KEY\":\"$AWS_SECRET_ACCESS_KEY\""
fi

if [ -n "$DATABASE_URL" ]; then
    if [ "$SECRET_JSON" != "{" ]; then
        SECRET_JSON="$SECRET_JSON,"
    fi
    SECRET_JSON="$SECRET_JSON\"DATABASE_URL\":\"$DATABASE_URL\""
fi

if [ -n "$REDIS_URL" ]; then
    if [ "$SECRET_JSON" != "{" ]; then
        SECRET_JSON="$SECRET_JSON,"
    fi
    SECRET_JSON="$SECRET_JSON\"REDIS_URL\":\"$REDIS_URL\""
fi

SECRET_JSON="$SECRET_JSON}"

# Create secret
echo ""
echo "🔐 Creating secret in AWS Secrets Manager..."
aws secretsmanager create-secret \
    --name $SECRET_NAME \
    --description "Secrets for Video Processor MVP application" \
    --secret-string "$SECRET_JSON" \
    --region $AWS_REGION

echo ""
echo "✅ Secret created successfully!"
echo ""
echo "📝 Secret ARN:"
aws secretsmanager describe-secret --secret-id $SECRET_NAME --region $AWS_REGION --query 'ARN' --output text
echo ""
echo "📋 To retrieve the secret:"
echo "   aws secretsmanager get-secret-value --secret-id $SECRET_NAME --region $AWS_REGION"
echo ""
echo "📋 To update the secret:"
echo "   aws secretsmanager update-secret --secret-id $SECRET_NAME --secret-string '{\"KEY\":\"VALUE\"}' --region $AWS_REGION"
echo ""
echo "⚠️  IMPORTANT: Save the SECRET_KEY securely if it was generated!"
if [ -n "$SECRET_KEY" ]; then
    echo "   SECRET_KEY: $SECRET_KEY"
fi

