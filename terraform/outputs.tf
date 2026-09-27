output "alb_dns_name" {
  description = "Public Application Load Balancer DNS endpoint"
  value       = aws_lb.nexus_alb.dns_name
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket storing enterprise documents"
  value       = aws_s3_bucket.documents_bucket.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS Fargate cluster"
  value       = aws_ecs_cluster.nexus_cluster.name
}

output "rds_endpoint" {
  description = "Connection endpoint for PostgreSQL RDS"
  value       = aws_db_instance.nexus_postgres.endpoint
}

output "bedrock_llm_model_id" {
  description = "Bedrock Foundation Model for reasoning"
  value       = var.bedrock_llm_model_id
}

output "bedrock_embed_model_id" {
  description = "Bedrock Foundation Model for embeddings"
  value       = var.bedrock_embed_model_id
}
