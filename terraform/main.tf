# Mini-OpenRAN Lab Terraform Configuration
# Deploy to AWS EC2 for cloud demo

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-22.04-amd64-server-*"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "EC2 Key Pair name (optional)"
  type        = string
  default     = ""
}

variable "github_sha" {
  description = "GitHub commit SHA for traceability"
  type        = string
  default     = "manual-deployment"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "demo"
}

# Local values
locals {
  name_prefix = "mini-openran-${var.environment}"
  
  tags = {
    Environment   = var.environment
    Project      = "mini-openran-lab"
    DeployedBy   = "terraform"
    GitCommit    = var.github_sha
    CostCenter   = "demo"
    AutoShutdown = "true"
  }
}

# VPC and networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(local.tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(local.tags, {
    Name = "${local.name_prefix}-igw"
  })
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = merge(local.tags, {
    Name = "${local.name_prefix}-rt"
  })
}

resource "aws_subnet" "main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  
  tags = merge(local.tags, {
    Name = "${local.name_prefix}-subnet"
  })
}

resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}

# Security group
resource "aws_security_group" "openran" {
  name_description = "${local.name_prefix}-sg"
  description = "Security group for Mini-OpenRAN Lab"
  vpc_id      = aws_vpc.main.id
  
  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }
  
  # Grafana dashboard
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Grafana dashboard"
  }
  
  # Prometheus
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Prometheus"
  }
  
  # xApp API
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "xApp API"
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = merge(local.tags, {
    Name = "${local.name_prefix}-sg"
  })
}

# User data script for EC2 instance
locals {
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    github_sha = var.github_sha
  }))
}

# EC2 instance
resource "aws_instance" "openran" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = var.key_name != "" ? var.key_name : null
  subnet_id             = aws_subnet.main.id
  vpc_security_group_ids = [aws_security_group.openran.id]
  user_data             = local.user_data
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
    
    tags = merge(local.tags, {
      Name = "${local.name_prefix}-root-volume"
    })
  }
  
  tags = merge(local.tags, {
    Name = "${local.name_prefix}-instance"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# Outputs
output "instance_public_ip" {
  description = "Public IP address of the OpenRAN instance"
  value       = aws_instance.openran.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the OpenRAN instance"
  value       = aws_instance.openran.public_dns
}

output "grafana_url" {
  description = "URL to access Grafana dashboard"
  value       = "http://${aws_instance.openran.public_ip}:3000"
}

output "prometheus_url" {
  description = "URL to access Prometheus"
  value       = "http://${aws_instance.openran.public_ip}:9090"
}

output "xapp_api_url" {
  description = "URL to access xApp API"
  value       = "http://${aws_instance.openran.public_ip}:8080"
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = var.key_name != "" ? "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.openran.public_ip}" : "SSH key not configured"
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    environment     = var.environment
    github_commit   = var.github_sha
    instance_type   = var.instance_type
    aws_region      = var.aws_region
    deployment_time = timestamp()
  }
}
