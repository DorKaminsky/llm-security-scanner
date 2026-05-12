resource "aws_cognito_user_pool" "main" {
  name = "llm-scanner-${var.environment}"

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  auto_verified_attributes = ["email"]

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  username_attributes      = ["email"]
  username_configuration { case_sensitive = false }

  user_pool_add_ons { advanced_security_mode = "ENFORCED" }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "llm-scanner-web-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  access_token_validity                = 1
  id_token_validity                    = 1
  refresh_token_validity               = 30
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
  prevent_user_existence_errors = "ENABLED"
}

output "user_pool_id"     { value = aws_cognito_user_pool.main.id }
output "user_pool_arn"    { value = aws_cognito_user_pool.main.arn }
output "user_pool_endpoint" { value = aws_cognito_user_pool.main.endpoint }
output "client_id"        { value = aws_cognito_user_pool_client.web.id }
