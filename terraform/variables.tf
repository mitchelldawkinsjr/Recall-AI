# Terraform variables for Video Processor MVP

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "video-processor"
}

variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "video-processor-cluster"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "video-processor-mvp"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = false
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for storage"
  type        = string
  default     = "video-processor-mvp-storage"
}

# RDS Variables
variable "enable_rds" {
  description = "Enable RDS PostgreSQL database"
  type        = bool
  default     = false
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "rds_database_name" {
  description = "RDS database name"
  type        = string
  default     = "video_recall_db"
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
  default     = "postgres"
}

variable "rds_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
  default     = "" # Should be set via terraform.tfvars or environment variable
}

