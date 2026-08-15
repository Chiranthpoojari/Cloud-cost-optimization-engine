output "lambda_function_name" {
  value = aws_lambda_function.cost_optimizer.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.cost_optimizer.arn
}

output "stop_rule_name" {
  value = aws_cloudwatch_event_rule.stop_schedule.name
}

output "start_rule_name" {
  value = aws_cloudwatch_event_rule.start_schedule.name
}

output "sns_topic_arn" {
  value = var.enable_sns_notifications ? aws_sns_topic.notifications[0].arn : null
}
