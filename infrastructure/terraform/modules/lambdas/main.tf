locals {
  services = {
    orchestrator        = { handler = "handler.handler", timeout = 30,  memory = 256, source = "scan-orchestrator" }
    prompt_injection    = { handler = "handler.handler", timeout = 120, memory = 256, source = "checkers/prompt-injection" }
    sensitive_disclosure = { handler = "handler.handler", timeout = 120, memory = 256, source = "checkers/sensitive-disclosure" }
    dos_resilience      = { handler = "handler.handler", timeout = 120, memory = 256, source = "checkers/dos-resilience" }
    excessive_agency    = { handler = "handler.handler", timeout = 120, memory = 256, source = "checkers/excessive-agency" }
    report_generator    = { handler = "handler.handler", timeout = 60,  memory = 512, source = "report-generator" }
    scan_status         = { handler = "handler.handler", timeout = 10,  memory = 128, source = "scan-status-api" }
  }

  common_env = {
    ENVIRONMENT        = var.environment
    SCANS_TABLE        = var.scans_table_name
    RESULTS_TABLE      = var.results_table_name
    CHECKS_QUEUE_URL   = var.checks_queue_url
    REPORTS_BUCKET     = var.reports_bucket
    LOG_LEVEL          = var.environment == "production" ? "WARNING" : "DEBUG"
  }
}

# IAM role shared base — each Lambda gets its own role via for_each
resource "aws_iam_role" "lambda" {
  for_each = local.services
  name     = "llm-scanner-${each.key}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  for_each   = local.services
  role       = aws_iam_role.lambda[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Orchestrator: DynamoDB write + SQS send + Secrets Manager create
resource "aws_iam_role_policy" "orchestrator" {
  name   = "orchestrator-policy"
  role   = aws_iam_role.lambda["orchestrator"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:PutItem", "dynamodb:UpdateItem"], Resource = var.scans_table_arn },
      { Effect = "Allow", Action = ["sqs:SendMessage"], Resource = var.checks_queue_arn },
      { Effect = "Allow", Action = ["secretsmanager:CreateSecret"], Resource = "arn:aws:secretsmanager:*:*:secret:scan/*" },
    ]
  })
}

# Checkers: DynamoDB read/write + SQS receive + Secrets Manager read
resource "aws_iam_role_policy" "checkers" {
  for_each = toset(["prompt_injection", "sensitive_disclosure", "dos_resilience", "excessive_agency"])
  name     = "${each.key}-policy"
  role     = aws_iam_role.lambda[each.key].id
  policy   = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:PutItem", "dynamodb:UpdateItem"], Resource = [var.results_table_arn, var.scans_table_arn] },
      { Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], Resource = var.checks_queue_arn },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = "arn:aws:secretsmanager:*:*:secret:scan/*" },
    ]
  })
}

# Report generator: DynamoDB read + S3 write
resource "aws_iam_role_policy" "report_generator" {
  name   = "report-generator-policy"
  role   = aws_iam_role.lambda["report_generator"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:UpdateItem"], Resource = [var.scans_table_arn, var.results_table_arn] },
      { Effect = "Allow", Action = ["dynamodb:ListStreams", "dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:DescribeStream"], Resource = var.scans_table_arn },
      { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject"], Resource = "${var.reports_bucket_arn}/*" },
    ]
  })
}

# Scan status: DynamoDB read only
resource "aws_iam_role_policy" "scan_status" {
  name   = "scan-status-policy"
  role   = aws_iam_role.lambda["scan_status"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:GetItem"], Resource = [var.scans_table_arn, var.results_table_arn] },
    ]
  })
}

# Lambda functions
resource "aws_lambda_function" "services" {
  for_each = local.services

  function_name = "llm-scanner-${each.key}-${var.environment}"
  role          = aws_iam_role.lambda[each.key].arn
  handler       = each.value.handler
  runtime       = "python3.12"
  timeout       = each.value.timeout
  memory_size   = each.value.memory
  filename      = "${path.module}/../../lambda-${replace(each.value.source, "/", "-")}.zip"

  environment {
    variables = local.common_env
  }

  depends_on = [aws_iam_role_policy_attachment.basic_execution]
}

# SQS → checker triggers
resource "aws_lambda_event_source_mapping" "checkers" {
  for_each         = toset(["prompt_injection", "sensitive_disclosure", "dos_resilience", "excessive_agency"])
  event_source_arn = var.checks_queue_arn
  function_name    = aws_lambda_function.services[each.key].arn
  batch_size       = 1
  filter_criteria {
    filter { pattern = jsonencode({ body = { check_type = [each.key] } }) }
  }
}

# DynamoDB stream → report generator
resource "aws_lambda_event_source_mapping" "report_trigger" {
  event_source_arn  = var.scans_stream_arn
  function_name     = aws_lambda_function.services["report_generator"].arn
  starting_position = "LATEST"
  batch_size        = 1
}

output "orchestrator_invoke_arn" { value = aws_lambda_function.services["orchestrator"].invoke_arn }
output "scan_status_invoke_arn"  { value = aws_lambda_function.services["scan_status"].invoke_arn }
output "orchestrator_arn"        { value = aws_lambda_function.services["orchestrator"].arn }
output "scan_status_arn"         { value = aws_lambda_function.services["scan_status"].arn }
