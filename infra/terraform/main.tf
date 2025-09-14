terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Backend configuration will be provided via -backend-config
    # bucket = "mincaai-terraform-state"
    # key    = "terraform.tfstate"
    # region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "mincaai"
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  
  name_prefix = local.name_prefix
  vpc_cidr    = var.vpc_cidr
  azs         = data.aws_availability_zones.available.names
  
  tags = local.common_tags
}

# Security
module "security" {
  source = "./modules/security"
  
  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  vpc_cidr    = var.vpc_cidr
  
  tags = local.common_tags
}

# Database
module "database" {
  source = "./modules/database"
  
  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  security_groups = [module.security.database_sg_id]
  
  db_instance_class = var.db_instance_class
  db_name          = var.db_name
  db_username      = var.db_username
  
  tags = local.common_tags
}

# Storage
module "storage" {
  source = "./modules/storage"
  
  name_prefix = local.name_prefix
  
  tags = local.common_tags
}

# Message Queues
module "queues" {
  source = "./modules/sqs"
  
  name_prefix = local.name_prefix
  
  queue_names = [
    "extractor",
    "codifier", 
    "transform",
    "exporter"
  ]
  
  tags = local.common_tags
}

# ECS Cluster
module "ecs" {
  source = "./modules/ecs"
  
  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  security_groups = [module.security.ecs_sg_id]
  
  tags = local.common_tags
}

# Load Balancer
module "alb" {
  source = "./modules/alb"
  
  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.public_subnet_ids
  security_groups = [module.security.alb_sg_id]
  
  tags = local.common_tags
}

# Secrets Manager
module "secrets" {
  source = "./modules/secrets"
  
  name_prefix = local.name_prefix
  
  secrets = {
    database_password = {
      description = "Database master password"
      value       = var.db_password
    }
    jwt_secret = {
      description = "JWT signing secret"
      value       = var.jwt_secret
    }
  }
  
  tags = local.common_tags
}

# CloudWatch
module "monitoring" {
  source = "./modules/monitoring"
  
  name_prefix = local.name_prefix
  
  tags = local.common_tags
}