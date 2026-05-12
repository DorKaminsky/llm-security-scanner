resource "aws_dynamodb_table" "scans" {
  name         = "llm-scanner-scans-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "scan_id"

  attribute { name = "scan_id"; type = "S" }
  attribute { name = "user_id"; type = "S" }

  global_secondary_index {
    name            = "user-scans-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  server_side_encryption { enabled = true }
  point_in_time_recovery { enabled = true }

  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"
}

resource "aws_dynamodb_table" "results" {
  name         = "llm-scanner-results-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "scan_id"
  range_key    = "check_type"

  attribute { name = "scan_id";    type = "S" }
  attribute { name = "check_type"; type = "S" }

  server_side_encryption { enabled = true }
}

output "scans_table_name" { value = aws_dynamodb_table.scans.name }
output "scans_table_arn"  { value = aws_dynamodb_table.scans.arn }
output "scans_stream_arn" { value = aws_dynamodb_table.scans.stream_arn }
output "results_table_name" { value = aws_dynamodb_table.results.name }
output "results_table_arn"  { value = aws_dynamodb_table.results.arn }
