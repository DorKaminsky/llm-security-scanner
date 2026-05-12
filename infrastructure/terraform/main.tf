terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "llm-scanner-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "llm-security-scanner"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "cognito" {
  source      = "./modules/cognito"
  environment = var.environment
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  environment = var.environment
}

module "sqs" {
  source      = "./modules/sqs"
  environment = var.environment
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
}

module "lambdas" {
  source      = "./modules/lambdas"
  environment = var.environment

  scans_table_name   = module.dynamodb.scans_table_name
  results_table_name = module.dynamodb.results_table_name
  checks_queue_url   = module.sqs.checks_queue_url
  reports_bucket     = module.s3.reports_bucket_name

  scans_table_arn    = module.dynamodb.scans_table_arn
  results_table_arn  = module.dynamodb.results_table_arn
  checks_queue_arn   = module.sqs.checks_queue_arn
  reports_bucket_arn = module.s3.reports_bucket_arn
  scans_stream_arn   = module.dynamodb.scans_stream_arn
}

module "api_gateway" {
  source      = "./modules/api-gateway"
  environment = var.environment

  cognito_user_pool_arn = module.cognito.user_pool_arn
  orchestrator_invoke_arn = module.lambdas.orchestrator_invoke_arn
  scan_status_invoke_arn  = module.lambdas.scan_status_invoke_arn
}

module "waf" {
  source      = "./modules/waf"
  environment = var.environment
  api_gateway_arn = module.api_gateway.arn
}

module "cloudfront" {
  source      = "./modules/cloudfront"
  environment = var.environment
  frontend_bucket_domain = module.s3.frontend_bucket_domain
  api_gateway_url        = module.api_gateway.invoke_url
}

output "frontend_url" {
  value = module.cloudfront.distribution_url
}

output "api_url" {
  value = module.api_gateway.invoke_url
}

output "frontend_bucket_name" {
  value = module.s3.frontend_bucket_name
}

output "cloudfront_distribution_id" {
  value = module.cloudfront.distribution_id
}
