# SecureBank Transaction Pipeline - Core Infrastructure
# This Terraform configuration creates the core AWS resources for the transaction processing pipeline

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  
  # Resource naming convention
  name_prefix = "${var.project_name}-${var.environment}"
  
  # Common tags
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
}

# ==========================================
# KMS Key for Encryption
# ==========================================
resource "aws_kms_key" "main" {
  description             = "KMS key for ${var.project_name} encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-encryption-key"
  })
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}-encryption"
  target_key_id = aws_kms_key.main.key_id
}

# ==========================================
# S3 Buckets
# ==========================================

# Raw transactions data lake
resource "aws_s3_bucket" "raw_transactions" {
  bucket = "${local.name_prefix}-transactions-raw-${local.account_id}"
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-transactions-raw"
    Purpose     = "Raw transaction data storage"
    DataClass   = "sensitive"
  })
}

resource "aws_s3_bucket_versioning" "raw_transactions" {
  bucket = aws_s3_bucket.raw_transactions.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_transactions" {
  bucket = aws_s3_bucket.raw_transactions.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "raw_transactions" {
  bucket = aws_s3_bucket.raw_transactions.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Processed transactions data
resource "aws_s3_bucket" "processed_transactions" {
  bucket = "${local.name_prefix}-transactions-processed-${local.account_id}"
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-transactions-processed"
    Purpose     = "Processed transaction data storage"
    DataClass   = "sensitive"
  })
}

resource "aws_s3_bucket_versioning" "processed_transactions" {
  bucket = aws_s3_bucket.processed_transactions.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_transactions" {
  bucket = aws_s3_bucket.processed_transactions.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "processed_transactions" {
  bucket = aws_s3_bucket.processed_transactions.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Deployment artifacts bucket
resource "aws_s3_bucket" "deployment" {
  bucket = "${local.name_prefix}-deployment-${local.account_id}"
  
  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-deployment"
    Purpose     = "Deployment artifacts storage"
    DataClass   = "internal"
  })
}

resource "aws_s3_bucket_versioning" "deployment" {
  bucket = aws_s3_bucket.deployment.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 lifecycle policies
resource "aws_s3_bucket_lifecycle_configuration" "raw_transactions" {
  bucket = aws_s3_bucket.raw_transactions.id

  rule {
    id     = "raw_transaction_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.environment == "prod" ? 2555 : 365  # 7 years for prod, 1 year for dev
    }
  }
}

# ==========================================
# DynamoDB Tables
# ==========================================

# Transactions table
resource "aws_dynamodb_table" "transactions" {
  name           = "${local.name_prefix}-transactions"
  billing_mode   = "ON_DEMAND"
  hash_key       = "customer_id"
  range_key      = "timestamp"
  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "merchant_id"
    type = "S"
  }

  global_secondary_index {
    name     = "TransactionIdIndex"
    hash_key = "transaction_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name     = "MerchantIndex"
    hash_key = "merchant_id"
    range_key = "timestamp"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-transactions"
    Purpose     = "Real-time transaction storage"
    DataClass   = "sensitive"
  })
}

# Customer profiles table
resource "aws_dynamodb_table" "customers" {
  name         = "${local.name_prefix}-customers"
  billing_mode = "ON_DEMAND"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-customers"
    Purpose     = "Customer profile storage"
    DataClass   = "sensitive"
  })
}

# ==========================================
# Kinesis Data Stream
# ==========================================
resource "aws_kinesis_stream" "transactions" {
  name        = "${local.name_prefix}-transactions"
  shard_count = var.kinesis_shard_count

  shard_level_metrics = [
    "IncomingRecords",
    "OutgoingRecords",
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  encryption_type = "KMS"
  kms_key_id      = aws_kms_key.main.arn

  retention_period = 24

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-transactions-stream"
    Purpose     = "Real-time transaction ingestion"
    DataClass   = "sensitive"
  })
}

# ==========================================
# IAM Roles and Policies
# ==========================================

# Lambda execution role
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.transactions.arn,
          aws_dynamodb_table.customers.arn,
          "${aws_dynamodb_table.transactions.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:PutObjectAcl"
        ]
        Resource = [
          "${aws_s3_bucket.raw_transactions.arn}/*",
          "${aws_s3_bucket.processed_transactions.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListStreams"
        ]
        Resource = aws_kinesis_stream.transactions.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# API Gateway execution role
resource "aws_iam_role" "api_gateway" {
  name = "${local.name_prefix}-api-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "api_gateway" {
  name = "${local.name_prefix}-api-gateway-policy"
  role = aws_iam_role.api_gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = aws_kinesis_stream.transactions.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Glue service role
resource "aws_iam_role" "glue_service" {
  name = "${local.name_prefix}-glue-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_service" {
  name = "${local.name_prefix}-glue-service-policy"
  role = aws_iam_role.glue_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_transactions.arn,
          "${aws_s3_bucket.raw_transactions.arn}/*",
          aws_s3_bucket.processed_transactions.arn,
          "${aws_s3_bucket.processed_transactions.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.main.arn
      }
    ]
  })
}

# ==========================================
# SNS Topic for Alerts
# ==========================================
resource "aws_sns_topic" "alerts" {
  name              = "${local.name_prefix}-alerts"
  kms_master_key_id = aws_kms_key.main.arn

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-alerts"
    Purpose     = "System alerts and notifications"
  })
}

resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# ==========================================
# CloudWatch Log Groups
# ==========================================
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.main.arn

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "lambda_processor" {
  name              = "/aws/lambda/${local.name_prefix}-transaction-processor"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.main.arn

  tags = local.common_tags
}

# ==========================================
# Glue Database
# ==========================================
resource "aws_glue_catalog_database" "analytics" {
  name        = "${replace(local.name_prefix, "-", "_")}_analytics"
  description = "Analytics database for ${var.project_name}"

  create_table_default_permission {
    permissions = ["ALL"]
    
    principal {
      data_lake_principal_identifier = "IAM_ALLOWED_PRINCIPALS"
    }
  }
}

# ==========================================
# Outputs
# ==========================================
output "s3_raw_bucket" {
  description = "Name of the raw transactions S3 bucket"
  value       = aws_s3_bucket.raw_transactions.bucket
}

output "s3_processed_bucket" {
  description = "Name of the processed transactions S3 bucket"
  value       = aws_s3_bucket.processed_transactions.bucket
}

output "dynamodb_transactions_table" {
  description = "Name of the transactions DynamoDB table"
  value       = aws_dynamodb_table.transactions.name
}

output "dynamodb_customers_table" {
  description = "Name of the customers DynamoDB table"
  value       = aws_dynamodb_table.customers.name
}

output "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  value       = aws_kinesis_stream.transactions.name
}

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "api_gateway_role_arn" {
  description = "ARN of the API Gateway execution role"
  value       = aws_iam_role.api_gateway.arn
}

output "glue_service_role_arn" {
  description = "ARN of the Glue service role"
  value       = aws_iam_role.glue_service.arn
}

output "sns_alerts_topic_arn" {
  description = "ARN of the SNS alerts topic"
  value       = aws_sns_topic.alerts.arn
}

output "kms_key_id" {
  description = "ID of the KMS encryption key"
  value       = aws_kms_key.main.key_id
}

output "glue_database_name" {
  description = "Name of the Glue analytics database"
  value       = aws_glue_catalog_database.analytics.name
}