#!/bin/bash

# ECS Auto-Scaling Setup Script
# Configures auto-scaling for ECS service based on CPU and memory utilization

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-2}"
CLUSTER_NAME="${CLUSTER_NAME:-video-processor-cluster}"
SERVICE_NAME="${SERVICE_NAME:-video-processor-service}"
MIN_CAPACITY="${MIN_CAPACITY:-2}"
MAX_CAPACITY="${MAX_CAPACITY:-10}"
CPU_TARGET="${CPU_TARGET:-70}"
MEMORY_TARGET="${MEMORY_TARGET:-80}"

echo "📈 Setting up ECS Auto-Scaling"
echo "=============================="

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

echo "✅ Found service: $SERVICE_NAME"
echo "   Service ARN: $SERVICE_ARN"
echo ""
echo "📋 Auto-scaling configuration:"
echo "   Min capacity: $MIN_CAPACITY tasks"
echo "   Max capacity: $MAX_CAPACITY tasks"
echo "   CPU target: $CPU_TARGET%"
echo "   Memory target: $MEMORY_TARGET%"
echo ""

# Register scalable target
echo "🎯 Registering scalable target..."
RESOURCE_ID="service/$CLUSTER_NAME/$SERVICE_NAME"

# Check if scalable target already exists
if aws application-autoscaling describe-scalable-targets \
    --service-namespace ecs \
    --resource-ids $RESOURCE_ID \
    --region $AWS_REGION \
    --query 'ScalableTargets[0].ResourceId' \
    --output text 2>/dev/null | grep -q "$RESOURCE_ID"; then
    echo "✅ Scalable target already exists, updating..."
    aws application-autoscaling register-scalable-target \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id $RESOURCE_ID \
        --min-capacity $MIN_CAPACITY \
        --max-capacity $MAX_CAPACITY \
        --region $AWS_REGION &>/dev/null || true
else
    aws application-autoscaling register-scalable-target \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id $RESOURCE_ID \
        --min-capacity $MIN_CAPACITY \
        --max-capacity $MAX_CAPACITY \
        --region $AWS_REGION
    echo "✅ Scalable target registered"
fi

# Create CPU-based scaling policy
echo ""
echo "📊 Creating CPU-based scaling policy..."
CPU_POLICY_NAME="video-processor-cpu-scaling"

if aws application-autoscaling describe-scaling-policies \
    --service-namespace ecs \
    --resource-id $RESOURCE_ID \
    --policy-names $CPU_POLICY_NAME \
    --region $AWS_REGION \
    --query 'ScalingPolicies[0].PolicyName' \
    --output text 2>/dev/null | grep -q "$CPU_POLICY_NAME"; then
    echo "   ⏭️  CPU policy already exists, updating..."
    aws application-autoscaling put-scaling-policy \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id $RESOURCE_ID \
        --policy-name $CPU_POLICY_NAME \
        --policy-type TargetTrackingScaling \
        --target-tracking-scaling-policy-configuration "{
            \"TargetValue\": $CPU_TARGET.0,
            \"PredefinedMetricSpecification\": {
                \"PredefinedMetricType\": \"ECSServiceAverageCPUUtilization\"
            },
            \"ScaleInCooldown\": 300,
            \"ScaleOutCooldown\": 60
        }" \
        --region $AWS_REGION &>/dev/null || true
else
    aws application-autoscaling put-scaling-policy \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id $RESOURCE_ID \
        --policy-name $CPU_POLICY_NAME \
        --policy-type TargetTrackingScaling \
        --target-tracking-scaling-policy-configuration "{
            \"TargetValue\": $CPU_TARGET.0,
            \"PredefinedMetricSpecification\": {
                \"PredefinedMetricType\": \"ECSServiceAverageCPUUtilization\"
            },
            \"ScaleInCooldown\": 300,
            \"ScaleOutCooldown\": 60
        }" \
        --region $AWS_REGION
    echo "   ✅ CPU scaling policy created"
fi

# Create Memory-based scaling policy
echo ""
echo "📊 Creating Memory-based scaling policy..."
MEMORY_POLICY_NAME="video-processor-memory-scaling"

if aws application-autoscaling describe-scaling-policies \
    --service-namespace ecs \
    --resource-id $RESOURCE_ID \
    --policy-names $MEMORY_POLICY_NAME \
    --region $AWS_REGION \
    --query 'ScalingPolicies[0].PolicyName' \
    --output text 2>/dev/null | grep -q "$MEMORY_POLICY_NAME"; then
    echo "   ⏭️  Memory policy already exists, updating..."
    aws application-autoscaling put-scaling-policy \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id $RESOURCE_ID \
        --policy-name $MEMORY_POLICY_NAME \
        --policy-type TargetTrackingScaling \
        --target-tracking-scaling-policy-configuration "{
            \"TargetValue\": $MEMORY_TARGET.0,
            \"PredefinedMetricSpecification\": {
                \"PredefinedMetricType\": \"ECSServiceAverageMemoryUtilization\"
            },
            \"ScaleInCooldown\": 300,
            \"ScaleOutCooldown\": 60
        }" \
        --region $AWS_REGION &>/dev/null || true
else
    aws application-autoscaling put-scaling-policy \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id $RESOURCE_ID \
        --policy-name $MEMORY_POLICY_NAME \
        --policy-type TargetTrackingScaling \
        --target-tracking-scaling-policy-configuration "{
            \"TargetValue\": $MEMORY_TARGET.0,
            \"PredefinedMetricSpecification\": {
                \"PredefinedMetricType\": \"ECSServiceAverageMemoryUtilization\"
            },
            \"ScaleInCooldown\": 300,
            \"ScaleOutCooldown\": 60
        }" \
        --region $AWS_REGION
    echo "   ✅ Memory scaling policy created"
fi

echo ""
echo "🎉 Auto-scaling setup completed!"
echo ""
echo "📋 Summary:"
echo "   Service: $SERVICE_NAME"
echo "   Min tasks: $MIN_CAPACITY"
echo "   Max tasks: $MAX_CAPACITY"
echo "   CPU target: $CPU_TARGET%"
echo "   Memory target: $MEMORY_TARGET%"
echo ""
echo "📝 Auto-scaling behavior:"
echo "   - Scales out when CPU > $CPU_TARGET% or Memory > $MEMORY_TARGET%"
echo "   - Scales in when both CPU < $CPU_TARGET% and Memory < $MEMORY_TARGET%"
echo "   - Scale-out cooldown: 60 seconds (fast scale-out)"
echo "   - Scale-in cooldown: 300 seconds (slow scale-in to prevent thrashing)"
echo ""
echo "📊 Monitor auto-scaling:"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].[runningCount,desiredCount]'"
echo ""
echo "   View in console:"
echo "   https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$CLUSTER_NAME/services/$SERVICE_NAME"

