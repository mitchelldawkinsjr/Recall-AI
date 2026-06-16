#!/bin/bash

# CloudWatch Monitoring and Alarms Setup Script
# Sets up comprehensive monitoring for Video Processor MVP

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-2}"
CLUSTER_NAME="${CLUSTER_NAME:-video-processor-cluster}"
SERVICE_NAME="${SERVICE_NAME:-video-processor-service}"
ALB_NAME="${ALB_NAME:-video-processor-alb}"
SNS_TOPIC_ARN="${SNS_TOPIC_ARN:-}"

echo "📊 Setting up CloudWatch Monitoring and Alarms"
echo "=============================================="

# Create SNS topic for alarms if not provided
if [ -z "$SNS_TOPIC_ARN" ]; then
    echo ""
    echo "📧 Creating SNS topic for alarms..."
    SNS_TOPIC_NAME="video-processor-alarms"
    
    if aws sns get-topic-attributes --topic-arn "arn:aws:sns:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):$SNS_TOPIC_NAME" --region $AWS_REGION &>/dev/null; then
        SNS_TOPIC_ARN="arn:aws:sns:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):$SNS_TOPIC_NAME"
        echo "✅ SNS topic already exists: $SNS_TOPIC_ARN"
    else
        SNS_TOPIC_ARN=$(aws sns create-topic --name $SNS_TOPIC_NAME --region $AWS_REGION --query 'TopicArn' --output text)
        echo "✅ SNS topic created: $SNS_TOPIC_ARN"
        echo ""
        echo "⚠️  IMPORTANT: Subscribe to this topic to receive alarm notifications:"
        echo "   aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com --region $AWS_REGION"
    fi
else
    echo "✅ Using provided SNS topic: $SNS_TOPIC_ARN"
fi

# Function to create alarm
create_alarm() {
    local ALARM_NAME=$1
    local METRIC_NAME=$2
    const NAMESPACE=$3
    local DIMENSIONS=$4
    local THRESHOLD=$5
    local COMPARISON=$6
    local EVALUATION_PERIODS=$7
    
    if aws cloudwatch describe-alarms --alarm-names $ALARM_NAME --region $AWS_REGION --query 'MetricAlarms[0].AlarmName' --output text 2>/dev/null | grep -q "$ALARM_NAME"; then
        echo "   ⏭️  Alarm already exists: $ALARM_NAME"
    else
        aws cloudwatch put-metric-alarm \
            --alarm-name "$ALARM_NAME" \
            --alarm-description "Alarm for $ALARM_NAME" \
            --metric-name "$METRIC_NAME" \
            --namespace "$NAMESPACE" \
            --statistic Average \
            --period 300 \
            --evaluation-periods $EVALUATION_PERIODS \
            --threshold $THRESHOLD \
            --comparison-operator $COMPARISON \
            --dimensions $DIMENSIONS \
            --alarm-actions $SNS_TOPIC_ARN \
            --region $AWS_REGION &>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Created alarm: $ALARM_NAME"
        else
            echo "   ⚠️  Failed to create alarm: $ALARM_NAME"
        fi
    fi
}

# ECS Service Alarms
echo ""
echo "🚨 Creating ECS Service Alarms..."

# High CPU utilization
create_alarm \
    "video-processor-high-cpu" \
    "CPUUtilization" \
    "AWS/ECS" \
    "Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME" \
    80 \
    "GreaterThanThreshold" \
    2

# High memory utilization
create_alarm \
    "video-processor-high-memory" \
    "MemoryUtilization" \
    "AWS/ECS" \
    "Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME" \
    85 \
    "GreaterThanThreshold" \
    2

# Task count too low
create_alarm \
    "video-processor-low-task-count" \
    "RunningTaskCount" \
    "AWS/ECS" \
    "Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME" \
    1 \
    "LessThanThreshold" \
    1

# Task count too high (cost control)
create_alarm \
    "video-processor-high-task-count" \
    "RunningTaskCount" \
    "AWS/ECS" \
    "Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME" \
    10 \
    "GreaterThanThreshold" \
    2

# ALB Alarms
echo ""
echo "🚨 Creating Application Load Balancer Alarms..."

# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names $ALB_NAME --region $AWS_REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || echo "")

if [ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ]; then
    ALB_ID=$(basename $ALB_ARN)
    
    # High 5xx error rate
    create_alarm \
        "video-processor-alb-high-5xx" \
        "HTTPCode_Target_5XX_Count" \
        "AWS/ApplicationELB" \
        "LoadBalancer=$ALB_ID" \
        10 \
        "GreaterThanThreshold" \
        2
    
    # High response time
    create_alarm \
        "video-processor-alb-high-latency" \
        "TargetResponseTime" \
        "AWS/ApplicationELB" \
        "LoadBalancer=$ALB_ID" \
        5 \
        "GreaterThanThreshold" \
        2
    
    # Unhealthy target count
    create_alarm \
        "video-processor-alb-unhealthy-targets" \
        "UnHealthyHostCount" \
        "AWS/ApplicationELB" \
        "LoadBalancer=$ALB_ID" \
        1 \
        "GreaterThanThreshold" \
        1
    
    echo "✅ ALB alarms created"
else
    echo "⚠️  ALB not found, skipping ALB alarms"
fi

# RDS Alarms (if RDS exists)
echo ""
echo "🚨 Creating RDS Alarms (if applicable)..."

DB_INSTANCE_IDENTIFIER="video-processor-db"
if aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_IDENTIFIER --region $AWS_REGION &>/dev/null; then
    # High CPU utilization
    create_alarm \
        "video-processor-rds-high-cpu" \
        "CPUUtilization" \
        "AWS/RDS" \
        "DBInstanceIdentifier=$DB_INSTANCE_IDENTIFIER" \
        80 \
        "GreaterThanThreshold" \
        2
    
    # High connection count
    create_alarm \
        "video-processor-rds-high-connections" \
        "DatabaseConnections" \
        "AWS/RDS" \
        "DBInstanceIdentifier=$DB_INSTANCE_IDENTIFIER" \
        80 \
        "GreaterThanThreshold" \
        2
    
    # Low free storage
    create_alarm \
        "video-processor-rds-low-storage" \
        "FreeStorageSpace" \
        "AWS/RDS" \
        "DBInstanceIdentifier=$DB_INSTANCE_IDENTIFIER" \
        10737418240 \
        "LessThanThreshold" \
        1
    
    echo "✅ RDS alarms created"
else
    echo "⚠️  RDS instance not found, skipping RDS alarms"
fi

# Create CloudWatch Dashboard
echo ""
echo "📊 Creating CloudWatch Dashboard..."

DASHBOARD_BODY=$(cat <<EOF
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/ECS", "CPUUtilization", "ServiceName", "$SERVICE_NAME", "ClusterName", "$CLUSTER_NAME"],
                    [".", "MemoryUtilization", ".", ".", ".", "."],
                    [".", "RunningTaskCount", ".", ".", ".", "."]
                ],
                "period": 300,
                "stat": "Average",
                "region": "$AWS_REGION",
                "title": "ECS Service Metrics"
            },
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "$ALB_ID"],
                    [".", "TargetResponseTime", ".", "."],
                    [".", "HTTPCode_Target_2XX_Count", ".", "."],
                    [".", "HTTPCode_Target_5XX_Count", ".", "."]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "$AWS_REGION",
                "title": "Load Balancer Metrics"
            },
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6
        }
    ]
}
EOF
)

if [ -n "$ALB_ID" ] && [ "$ALB_ID" != "None" ]; then
    aws cloudwatch put-dashboard \
        --dashboard-name "VideoProcessor-Monitoring" \
        --dashboard-body "$DASHBOARD_BODY" \
        --region $AWS_REGION &>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ CloudWatch Dashboard created"
        echo "   View at: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=VideoProcessor-Monitoring"
    else
        echo "⚠️  Failed to create dashboard"
    fi
else
    echo "⚠️  ALB not found, skipping dashboard creation"
fi

echo ""
echo "🎉 Monitoring setup completed!"
echo ""
echo "📋 Summary:"
echo "   SNS Topic: $SNS_TOPIC_ARN"
echo "   Alarms created for:"
echo "     - ECS CPU/Memory/Task Count"
echo "     - ALB Errors/Latency/Health"
echo "     - RDS CPU/Connections/Storage (if applicable)"
echo ""
echo "📝 Next steps:"
echo "   1. Subscribe to SNS topic to receive alarm notifications:"
echo "      aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com --region $AWS_REGION"
echo "   2. View dashboard: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=VideoProcessor-Monitoring"
echo "   3. Customize alarm thresholds as needed"

