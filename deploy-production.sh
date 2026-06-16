#!/bin/bash

# Unified Production Deployment Script
# Master script for deploying to EC2 or ECS

set -e

# Configuration
DEPLOYMENT_TARGET="${1:-ec2}"  # ec2 or ecs
EC2_IP="${EC2_IP:-18.220.86.138}"
AWS_REGION="${AWS_REGION:-us-east-2}"

echo "🚀 Video Processor MVP - Production Deployment"
echo "=============================================="
echo "Deployment Target: $DEPLOYMENT_TARGET"
echo ""

# Validate prerequisites
echo "🔍 Validating prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI not found"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS credentials not configured"
    exit 1
fi

# Check Docker (for ECS deployments)
if [ "$DEPLOYMENT_TARGET" = "ecs" ]; then
    if ! command -v docker &> /dev/null; then
        echo "❌ Error: Docker not found (required for ECS deployment)"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Error: Docker is not running"
        exit 1
    fi
fi

# Check SSH key (for EC2 deployments)
if [ "$DEPLOYMENT_TARGET" = "ec2" ]; then
    SSH_KEY="${SSH_KEY:-video-processor-key.pem}"
    if [ ! -f "$SSH_KEY" ]; then
        echo "❌ Error: SSH key not found: $SSH_KEY"
        exit 1
    fi
fi

echo "✅ Prerequisites validated"
echo ""

# Deploy based on target
case "$DEPLOYMENT_TARGET" in
    ec2)
        echo "🖥️  Deploying to EC2..."
        echo ""
        if [ -f "./deploy-ec2.sh" ]; then
            bash ./deploy-ec2.sh
        else
            echo "❌ Error: deploy-ec2.sh not found"
            exit 1
        fi
        ;;
    ecs)
        echo "☁️  Deploying to ECS..."
        echo ""
        if [ -f "./deploy-aws-simple.sh" ]; then
            bash ./deploy-aws-simple.sh
        else
            echo "❌ Error: deploy-aws-simple.sh not found"
            exit 1
        fi
        ;;
    both)
        echo "🔄 Deploying to both EC2 and ECS..."
        echo ""
        echo "Step 1: Deploying to EC2..."
        if [ -f "./deploy-ec2.sh" ]; then
            bash ./deploy-ec2.sh || echo "⚠️  EC2 deployment had issues"
        fi
        echo ""
        echo "Step 2: Deploying to ECS..."
        if [ -f "./deploy-aws-simple.sh" ]; then
            bash ./deploy-aws-simple.sh || echo "⚠️  ECS deployment had issues"
        fi
        ;;
    *)
        echo "❌ Error: Invalid deployment target: $DEPLOYMENT_TARGET"
        echo "Usage: $0 [ec2|ecs|both]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment process completed!"
echo ""
echo "📊 Check deployment status:"
echo "   ./deployment-status.sh"
echo ""

