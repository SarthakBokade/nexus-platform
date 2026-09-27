# Amazon ECS Fargate Cluster & Application Load Balancer

resource "aws_ecs_cluster" "nexus_cluster" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}

# --- Security Groups ---
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-alb-sg"
  description = "Controls HTTP traffic to Application Load Balancer"
  vpc_id      = aws_vpc.nexus_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_tasks_sg" {
  name        = "${var.project_name}-tasks-sg"
  description = "Allows ingress from ALB to ECS Fargate tasks"
  vpc_id      = aws_vpc.nexus_vpc.id

  ingress {
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Application Load Balancer ---
resource "aws_lb" "nexus_alb" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]
}

resource "aws_lb_target_group" "nexus_tg" {
  name        = "${var.project_name}-tg"
  port        = var.app_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.nexus_vpc.id
  target_type = "ip"

  health_check {
    path                = "/api/v1/health"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_lb.nexus_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nexus_tg.arn
  }
}

# --- Task Definition & Service ---
resource "aws_ecs_task_definition" "nexus_task" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.container_cpu)
  memory                   = tostring(var.container_memory)
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "nexus-backend"
      image     = "public.ecr.aws/nexus/backend:latest"
      essential = true
      portMappings = [
        {
          containerPort = var.app_port
          hostPort      = var.app_port
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "AWS_BEDROCK_ENABLED", value = "True" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "BEDROCK_LLM_MODEL_ID", value = var.bedrock_llm_model_id },
        { name = "BEDROCK_EMBED_MODEL_ID", value = var.bedrock_embed_model_id },
        { name = "S3_BUCKET_NAME", value = aws_s3_bucket.documents_bucket.id }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "nexus"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "nexus_service" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.nexus_cluster.id
  task_definition = aws_ecs_task_definition.nexus_task.arn
  launch_type     = "FARGATE"
  desired_count   = 2

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_tasks_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.nexus_tg.arn
    container_name   = "nexus-backend"
    container_port   = var.app_port
  }

  depends_on = [aws_lb_listener.http_listener]
}
