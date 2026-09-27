variable "aws_region" {
  description = "The AWS region to deploy NEXUS infrastructure into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project identifier"
  type        = string
  default     = "nexus-platform"
}

variable "bedrock_llm_model_id" {
  description = "Amazon Bedrock Foundation Model ID for agentic reasoning"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "bedrock_embed_model_id" {
  description = "Amazon Bedrock Foundation Model ID for text embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "s3_bucket_name" {
  description = "S3 Bucket for storing enterprise PDF source documents"
  type        = string
  default     = "nexus-enterprise-documents-storage"
}

variable "app_port" {
  description = "Application port inside Docker container"
  type        = number
  default     = 8000
}

variable "container_cpu" {
  description = "Fargate CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "container_memory" {
  description = "Fargate Memory in MB"
  type        = number
  default     = 2048
}
