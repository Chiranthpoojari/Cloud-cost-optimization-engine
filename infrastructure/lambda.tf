data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_function.py"
  output_path = "${path.module}/build/lambda_function.zip"
}

resource "aws_lambda_function" "cost_optimizer" {
  function_name    = "${var.project_name}-engine"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 128
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      SCHEDULE_TAG_KEY   = var.schedule_tag_key
      SCHEDULE_TAG_VALUE = var.schedule_tag_value
      ENV_TAG_KEY        = var.env_tag_key
      NON_PROD_ENVS      = var.non_prod_envs
      DRY_RUN            = tostring(var.dry_run)
      SNS_TOPIC_ARN      = var.enable_sns_notifications ? aws_sns_topic.notifications[0].arn : ""
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.cost_optimizer.function_name}"
  retention_in_days = 30
}
