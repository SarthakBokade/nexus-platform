# Amazon RDS PostgreSQL Database with pgvector Extension Support

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${var.project_name}-rds-subnets"
  subnet_ids = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Allows PostgreSQL traffic from ECS tasks"
  vpc_id      = aws_vpc.nexus_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "nexus_postgres" {
  identifier             = "${var.project_name}-postgres"
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = "db.t4g.medium"
  allocated_storage      = 50
  max_allocated_storage  = 200
  storage_type           = "gp3"
  db_name                = "nexusdb"
  username               = "nexus_admin"
  password               = "SecureProductionPassword2025!" # In production, provision via AWS Secrets Manager
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true
  publicly_accessible    = false

  tags = {
    Name = "${var.project_name}-database"
  }
}
