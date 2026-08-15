resource "aws_cloudwatch_event_rule" "stop_schedule" {
  name                = "${var.project_name}-stop"
  description         = "Triggers cost optimizer to stop tagged non-prod resources"
  schedule_expression = var.stop_schedule_expression
}

resource "aws_cloudwatch_event_target" "stop_target" {
  rule = aws_cloudwatch_event_rule.stop_schedule.name
  arn  = aws_lambda_function.cost_optimizer.arn
  input = jsonencode({ action = "stop" })
}

resource "aws_lambda_permission" "allow_eventbridge_stop" {
  statement_id  = "AllowExecutionFromEventBridgeStop"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stop_schedule.arn
}

resource "aws_cloudwatch_event_rule" "start_schedule" {
  name                = "${var.project_name}-start"
  description         = "Triggers cost optimizer to start tagged non-prod resources"
  schedule_expression = var.start_schedule_expression
}

resource "aws_cloudwatch_event_target" "start_target" {
  rule = aws_cloudwatch_event_rule.start_schedule.name
  arn  = aws_lambda_function.cost_optimizer.arn
  input = jsonencode({ action = "start" })
}

resource "aws_lambda_permission" "allow_eventbridge_start" {
  statement_id  = "AllowExecutionFromEventBridgeStart"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.start_schedule.arn
}
