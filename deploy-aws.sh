#!/bin/bash

# AWS Deployment Script for Video Processor MVP
# This script deploys the application to AWS ECS Fargate

set -e

echo "🚀 Deploying Video Processor MVP to AWS"
echo "======================================="

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

# Check Docker
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop"
    exit 1
fi

echo "✅ All prerequisites met"

# Set variables
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="video-processor-mvp"
CLUSTER_NAME="video-processor-cluster"
SERVICE_NAME="video-processor-service"

echo ""
echo "📋 Deployment Configuration:"
echo "   AWS Region: $AWS_REGION"
echo "   AWS Account: $AWS_ACCOUNT_ID"
echo "   ECR Repository: $ECR_REPOSITORY"
echo "   ECS Cluster: $CLUSTER_NAME"
echo "   ECS Service: $SERVICE_NAME"

# Step 1: Create ECR repository
echo ""
echo "📦 Step 1: Creating ECR repository..."
if aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION &> /dev/null; then
    echo "✅ ECR repository already exists"
else
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    echo "✅ ECR repository created"
fi

# Step 2: Login to ECR
echo ""
echo "🔐 Step 2: Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 3: Build and push Docker image
echo ""
echo "🏗️  Step 3: Building and pushing Docker image..."
docker build -f Dockerfile.prod -t $ECR_REPOSITORY .
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

echo "✅ Docker image pushed to ECR"

# Step 4: Create VPC and networking (if not exists)
echo ""
echo "🌐 Step 4: Setting up networking..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=video-processor-vpc" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)

if [ "$VPC_ID" = "None" ] || [ "$VPC_ID" = "" ]; then
    echo "Creating VPC and networking resources..."
    
    # Create VPC
    VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=video-processor-vpc}]' --query 'Vpc.VpcId' --output text --region $AWS_REGION)
    
    # Create Internet Gateway
    IGW_ID=$(aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=video-processor-igw}]' --query 'InternetGateway.InternetGatewayId' --output text --region $AWS_REGION)
    aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID --region $AWS_REGION
    
    # Create public subnets
    SUBNET_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone ${AWS_REGION}a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=video-processor-subnet-1}]' --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
    SUBNET_2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone ${AWS_REGION}b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=video-processor-subnet-2}]' --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
    
    # Create route table
    ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=video-processor-rt}]' --query 'RouteTable.RouteTableId' --output text --region $AWS_REGION)
    aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID --region $AWS_REGION
    
    # Associate subnets with route table
    aws ec2 associate-route-table --subnet-id $SUBNET_1 --route-table-id $ROUTE_TABLE_ID --region $AWS_REGION
    aws ec2 associate-route-table --subnet-id $SUBNET_2 --route-table-id $ROUTE_TABLE_ID --region $AWS_REGION
    
    echo "✅ VPC and networking created"
else
    echo "✅ VPC already exists: $VPC_ID"
fi

# Step 5: Create security group
echo ""
echo "🔒 Step 5: Creating security group..."
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=video-processor-sg" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)

if [ "$SECURITY_GROUP_ID" = "None" ] || [ "$SECURITY_GROUP_ID" = "" ]; then
    SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name video-processor-sg --description "Security group for Video Processor MVP" --vpc-id $VPC_ID --query 'GroupId' --output text --region $AWS_REGION)
    
    # Allow HTTP and HTTPS traffic
    aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $AWS_REGION
    aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $AWS_REGION
    aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $AWS_REGION
    
    echo "✅ Security group created: $SECURITY_GROUP_ID"
else
    echo "✅ Security group already exists: $SECURITY_GROUP_ID"
fi

# Step 6: Create Application Load Balancer
echo ""
echo "⚖️  Step 6: Creating Application Load Balancer..."
ALB_ARN=$(aws elbv2 describe-load-balancers --names video-processor-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $AWS_REGION)

if [ "$ALB_ARN" = "None" ] || [ "$ALB_ARN" = "" ]; then
    ALB_ARN=$(aws elbv2 create-load-balancer --name video-processor-alb --subnets $SUBNET_1 $SUBNET_2 --security-groups $SECURITY_GROUP_ID --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $AWS_REGION)
    echo "✅ Application Load Balancer created: $ALB_ARN"
else
    echo "✅ Application Load Balancer already exists: $ALB_ARN"
fi

# Step 7: Create ECS cluster
echo ""
echo "🎯 Step 7: Creating ECS cluster..."
if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text | grep -q "ACTIVE"; then
    echo "✅ ECS cluster already exists"
else
    aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION
    echo "✅ ECS cluster created"
fi

# Step 8: Create task definition
echo ""
echo "📋 Step 8: Creating ECS task definition..."
cat > task-definition.json << EOF
{
    "family": "video-processor-task",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "video-processor",
            "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "environment": [
                {
                    "name": "DJANGO_SETTINGS_MODULE",
                    "value": "video_recall_project.settings.production"
                },
                {
                    "name": "DEBUG",
                    "value": "False"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/video-processor",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF

aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION
echo "✅ ECS task definition created"

# Step 9: Create ECS service
echo ""
echo "🚀 Step 9: Creating ECS service..."
if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text | grep -q "ACTIVE"; then
    echo "✅ ECS service already exists"
else
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition video-processor-task \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:$AWS_REGION:$AWS_ACCOUNT_ID:targetgroup/video-processor-tg/$(aws elbv2 describe-target-groups --names video-processor-tg --query 'TargetGroups[0].TargetGroupArn' --output text --region $AWS_REGION | cut -d'/' -f2),containerName=video-processor,containerPort=8000" \
        --region $AWS_REGION
    echo "✅ ECS service created"
fi

# Step 10: Get load balancer URL
echo ""
echo "🌐 Step 10: Getting deployment URL..."
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].DNSName' --output text --region $AWS_REGION)

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "   ECR Repository: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
echo "   ECS Cluster: $CLUSTER_NAME"
echo "   ECS Service: $SERVICE_NAME"
echo "   Load Balancer: $ALB_DNS"
echo ""
echo "🔗 Your application will be available at:"
echo "   http://$ALB_DNS"
echo ""
echo "⏳ Please wait 5-10 minutes for the service to fully start up."
echo "📋 You can monitor the deployment in the AWS Console:"
echo "   ECS: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$CLUSTER_NAME/services"
echo "   Load Balancer: https://console.aws.amazon.com/ec2/v2/home?region=$AWS_REGION#LoadBalancers:"

# Cleanup
rm -f task-definition.json

echo ""
echo "✅ AWS deployment script completed!"




