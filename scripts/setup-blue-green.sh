#!/bin/bash

# Blue/Green Deployment Setup Script for ECS
# Sets up CodeDeploy for zero-downtime deployments

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-2}"
CLUSTER_NAME="${CLUSTER_NAME:-video-processor-cluster}"
SERVICE_NAME="${SERVICE_NAME:-video-processor-service}"
APPLICATION_NAME="${APPLICATION_NAME:-VideoProcessorApp}"
DEPLOYMENT_GROUP_NAME="${DEPLOYMENT_GROUP_NAME:-VideoProcessorDeploymentGroup}"
TARGET_GROUP_1="${TARGET_GROUP_1:-}"
TARGET_GROUP_2="${TARGET_GROUP_2:-}"

echo "🔄 Setting up Blue/Green Deployments with CodeDeploy"
echo "===================================================="

# Get service ARN
SERVICE_ARN=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --query 'services[0].serviceArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$SERVICE_ARN" ] || [ "$SERVICE_ARN" = "None" ]; then
    echo "❌ Error: ECS service not found: $SERVICE_NAME"
    echo "   Please deploy the service first using deploy-aws-simple.sh"
    exit 1
fi

# Get load balancer and target groups
echo "🔍 Getting load balancer information..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --region $AWS_REGION \
    --query "LoadBalancers[?contains(LoadBalancerName, 'video-processor')].LoadBalancerArn" \
    --output text | head -1)

if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" = "None" ]; then
    echo "❌ Error: Load balancer not found"
    exit 1
fi

echo "✅ Found load balancer: $ALB_ARN"

# Get target groups
TARGET_GROUPS=$(aws elbv2 describe-target-groups \
    --region $AWS_REGION \
    --query "TargetGroups[?contains(TargetGroupName, 'video-processor')].TargetGroupArn" \
    --output text)

TARGET_GROUP_ARNS=($TARGET_GROUPS)

if [ ${#TARGET_GROUP_ARNS[@]} -lt 1 ]; then
    echo "❌ Error: Target groups not found"
    exit 1
fi

# Use first target group as primary, create second if needed
TARGET_GROUP_1="${TARGET_GROUP_ARNS[0]}"
echo "✅ Primary target group: $TARGET_GROUP_1"

# Create second target group for blue/green if it doesn't exist
TARGET_GROUP_2_NAME="video-processor-tg-green"
TARGET_GROUP_2=$(aws elbv2 describe-target-groups \
    --names $TARGET_GROUP_2_NAME \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$TARGET_GROUP_2" ] || [ "$TARGET_GROUP_2" = "None" ]; then
    echo "📦 Creating second target group for blue/green deployments..."
    VPC_ID=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $ALB_ARN \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].VpcId' \
        --output text)
    
    TARGET_GROUP_2=$(aws elbv2 create-target-group \
        --name $TARGET_GROUP_2_NAME \
        --protocol HTTP \
        --port 8000 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-path /api/health/ \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 10 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 5 \
        --region $AWS_REGION \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)
    
    echo "✅ Created second target group: $TARGET_GROUP_2"
else
    echo "✅ Second target group already exists: $TARGET_GROUP_2"
fi

# Create CodeDeploy application
echo ""
echo "📱 Creating CodeDeploy application..."
if aws deploy get-application \
    --application-name $APPLICATION_NAME \
    --region $AWS_REGION &>/dev/null; then
    echo "✅ CodeDeploy application already exists"
else
    aws deploy create-application \
        --application-name $APPLICATION_NAME \
        --compute-platform ECS \
        --region $AWS_REGION
    echo "✅ CodeDeploy application created"
fi

# Create IAM role for CodeDeploy if needed
echo ""
echo "🔐 Checking IAM role for CodeDeploy..."
CODE_DEPLOY_ROLE_NAME="CodeDeployServiceRole"
CODE_DEPLOY_ROLE_ARN=$(aws iam get-role \
    --role-name $CODE_DEPLOY_ROLE_NAME \
    --query 'Role.Arn' \
    --output text 2>/dev/null || echo "")

if [ -z "$CODE_DEPLOY_ROLE_ARN" ] || [ "$CODE_DEPLOY_ROLE_ARN" = "None" ]; then
    echo "⚠️  CodeDeploy service role not found. Creating..."
    
    # Create trust policy
    cat > /tmp/codedeploy-trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "codedeploy.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
    
    # Create role
    CODE_DEPLOY_ROLE_ARN=$(aws iam create-role \
        --role-name $CODE_DEPLOY_ROLE_NAME \
        --assume-role-policy-document file:///tmp/codedeploy-trust-policy.json \
        --query 'Role.Arn' \
        --output text)
    
    # Attach policy
    aws iam attach-role-policy \
        --role-name $CODE_DEPLOY_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole
    
    echo "✅ CodeDeploy service role created: $CODE_DEPLOY_ROLE_ARN"
    rm /tmp/codedeploy-trust-policy.json
else
    echo "✅ CodeDeploy service role exists: $CODE_DEPLOY_ROLE_ARN"
fi

# Create deployment group
echo ""
echo "📦 Creating deployment group..."
if aws deploy get-deployment-group \
    --application-name $APPLICATION_NAME \
    --deployment-group-name $DEPLOYMENT_GROUP_NAME \
    --region $AWS_REGION &>/dev/null; then
    echo "✅ Deployment group already exists"
else
    aws deploy create-deployment-group \
        --application-name $APPLICATION_NAME \
        --deployment-group-name $DEPLOYMENT_GROUP_NAME \
        --service-role-arn $CODE_DEPLOY_ROLE_ARN \
        --ecs-services "clusterName=$CLUSTER_NAME,serviceName=$SERVICE_NAME" \
        --load-balancer-info "{
            \"targetGroupInfoList\": [
                {\"name\": \"$(basename $TARGET_GROUP_1)\"},
                {\"name\": \"$(basename $TARGET_GROUP_2)\"}
            ]
        }" \
        --blue-green-deployment-configuration "{
            \"terminateBlueInstancesOnDeploymentSuccess\": {
                \"action\": \"TERMINATE\",
                \"terminationWaitTimeInMinutes\": 5
            },
            \"deploymentReadyOption\": {
                \"actionOnTimeout\": \"CONTINUE_DEPLOYMENT\",
                \"waitTimeInMinutes\": 0
            },
            \"greenFleetProvisioningOption\": {
                \"action\": \"COPY_AUTO_SCALING_GROUP\"
            }
        }" \
        --auto-rollback-configuration "{
            \"enabled\": true,
            \"events\": [\"DEPLOYMENT_FAILURE\", \"DEPLOYMENT_STOP_ON_ALARM\", \"DEPLOYMENT_STOP_ON_REQUEST\"]
        }" \
        --region $AWS_REGION
    
    echo "✅ Deployment group created"
fi

echo ""
echo "🎉 Blue/Green deployment setup completed!"
echo ""
echo "📋 Summary:"
echo "   Application: $APPLICATION_NAME"
echo "   Deployment Group: $DEPLOYMENT_GROUP_NAME"
echo "   ECS Service: $SERVICE_NAME"
echo "   Cluster: $CLUSTER_NAME"
echo "   Target Groups:"
echo "     - Blue: $(basename $TARGET_GROUP_1)"
echo "     - Green: $(basename $TARGET_GROUP_2)"
echo ""
echo "📝 To deploy using blue/green:"
echo "   1. Create an appspec.yml file (see example below)"
echo "   2. Create a deployment:"
echo "      aws deploy create-deployment \\"
echo "        --application-name $APPLICATION_NAME \\"
echo "        --deployment-group-name $DEPLOYMENT_GROUP_NAME \\"
echo "        --revision revisionType=AppSpecContent,appSpecContent={content=$(cat appspec.yml | base64)} \\"
echo "        --region $AWS_REGION"
echo ""
echo "📄 Example appspec.yml:"
cat <<'APPSPEC_EOF'
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION_ARN>
        LoadBalancerInfo:
          ContainerName: video-processor
          ContainerPort: 8000
APPSPEC_EOF

echo ""
echo "📊 Monitor deployments:"
echo "   https://console.aws.amazon.com/codesuite/codedeploy/applications/$APPLICATION_NAME/deployment-groups/$DEPLOYMENT_GROUP_NAME?region=$AWS_REGION"

