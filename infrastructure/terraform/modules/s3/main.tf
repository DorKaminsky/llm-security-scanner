resource "aws_s3_bucket" "reports" {
  bucket = "llm-scanner-reports-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "frontend" {
  bucket = "llm-scanner-frontend-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    id     = "expire-old-reports"
    status = "Enabled"
    expiration { days = 90 }
  }
}

data "aws_caller_identity" "current" {}

output "reports_bucket_name"   { value = aws_s3_bucket.reports.bucket }
output "reports_bucket_arn"    { value = aws_s3_bucket.reports.arn }
output "frontend_bucket_name"  { value = aws_s3_bucket.frontend.bucket }
output "frontend_bucket_arn"   { value = aws_s3_bucket.frontend.arn }
output "frontend_bucket_domain" { value = aws_s3_bucket.frontend.bucket_regional_domain_name }
