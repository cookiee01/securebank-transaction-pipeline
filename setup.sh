#!/bin/bash

# SecureBank Transaction Pipeline Setup Script
# This script sets up the development environment and validates prerequisites

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate AWS CLI access
validate_aws() {
    log_info "Validating AWS CLI access..."
    
    if ! command_exists aws; then
        log_error "AWS CLI not found. Please install AWS CLI first."
        echo "Installation instructions: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        return 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured or invalid."
        echo "Run 'aws configure' to set up your credentials."
        return 1
    fi
    
    # Get AWS account info
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region || echo "us-east-1")
    
    log_success "AWS CLI configured successfully"
    log_info "Account ID: $AWS_ACCOUNT_ID"
    log_info "Region: $AWS_REGION"
    
    return 0
}

# Main setup function
main() {
    echo "========================================"
    echo "SecureBank Transaction Pipeline Setup"
    echo "========================================"
    echo
    
    # Check prerequisites
    log_info "Checking prerequisites..."
    
    if ! validate_aws; then
        log_error "AWS validation failed. Please fix AWS configuration and try again."
        exit 1
    fi
    
    log_success "Setup completed successfully!"
}

# Run main setup
main
