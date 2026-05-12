resource "aws_sqs_queue" "checks_dlq" {
  name                      = "llm-scanner-checks-dlq-${var.environment}.fifo"
  fifo_queue                = true
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "checks" {
  name                        = "llm-scanner-checks-${var.environment}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 300
  message_retention_seconds   = 3600
  sqs_managed_sse_enabled     = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.checks_dlq.arn
    maxReceiveCount     = 3
  })
}

output "checks_queue_url" { value = aws_sqs_queue.checks.url }
output "checks_queue_arn" { value = aws_sqs_queue.checks.arn }
output "checks_dlq_arn"   { value = aws_sqs_queue.checks_dlq.arn }
