resource "aws_sns_topic" "notifications" {
  count = var.enable_sns_notifications ? 1 : 0
  name  = "${var.project_name}-notifications"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.enable_sns_notifications && var.notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.notifications[0].arn
  protocol  = "email"
  endpoint  = var.notification_email
}
