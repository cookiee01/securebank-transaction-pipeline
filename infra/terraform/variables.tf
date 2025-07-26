# SecureBank Transaction Pipeline - Terraform Variables
# This file defines all configurable variables for the infrastructure

# ==========================================
# General Configuration
# ==========================================
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition = can(regex("^[a-z0-9-]+$", var.aws_region))
    error_message = "AWS region must be a valid region identifier."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "securebank"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "platform-team"
}

# ==========================================
# Kinesis Configuration
# ==========================================
variable "kinesis_shard_count" {
  description = "Number of shards for Kinesis data stream"
  type        = number
  default     = 2
  
  validation {
    condition     = var.kinesis_shard_count >= 1 && var.kinesis_shard_count <= 40
    error_message = "Kinesis shard count must be between 1 and 40."
  }
}

variable "kinesis_retention_period" {
  description = "Data retention period for Kinesis stream (hours)"
  type        = number
  default     = 24
  
  validation {
    condition     = var.kinesis_retention_period >= 24 && var.kinesis_retention_period <= 8760
    error_message = "Kinesis retention period must be between 24 and 8760 hours."
  }
}

# ==========================================
# Monitoring Configuration
# ==========================================
variable "notification_email" {
  description = "Email address for notifications"
  type        = string
  default     = ""
  
  validation {
    condition = var.notification_email == "" || can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.notification_email))
    error_message = "Notification email must be a valid email address."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7
  
  validation {
    condition = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# ==========================================
# Cost Control Configuration
# ==========================================
variable "budget_limit_monthly" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 200
  
  validation {
    condition     = var.budget_limit_monthly > 0
    error_message = "Monthly budget limit must be greater than 0."
  }
}

variable "budget_alert_threshold" {
  description = "Budget alert threshold (percentage of limit)"
  type        = number
  default     = 80
  
  validation {
    condition     = var.budget_alert_threshold > 0 && var.budget_alert_threshold <= 100
    error_message = "Budget alert threshold must be between 0 and 100."
  }
}

# ==========================================
# Fraud Detection Configuration
# ==========================================
variable "fraud_threshold" {
  description = "Risk score threshold for fraud detection"
  type        = number
  default     = 0.8
  
  validation {
    condition     = var.fraud_threshold >= 0 && var.fraud_threshold <= 1
    error_message = "Fraud threshold must be between 0 and 1."
  }
}

variable "velocity_threshold" {
  description = "Number of transactions threshold for velocity fraud"
  type        = number
  default     = 5
  
  validation {
    condition     = var.velocity_threshold > 0
    error_message = "Velocity threshold must be greater than 0."
  }
}

variable "amount_anomaly_multiplier" {
  description = "Multiplier for amount anomaly detection"
  type        = number
  default     = 3.0
  
  validation {
    condition     = var.amount_anomaly_multiplier > 1
    error_message = "Amount anomaly multiplier must be greater than 1."
  }
}