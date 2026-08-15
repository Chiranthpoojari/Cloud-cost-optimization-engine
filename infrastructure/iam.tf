data "aws_caller_identity" "current" {}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  # Discovery + describe calls are read-only and can't be tag-scoped by IAM
  # (they operate before we know which resources match). The actual
  # stop/start mutation calls ARE scoped to resources carrying the
  # AutoSchedule tag, so a bug in the code's own filtering logic can't
  # widen the blast radius beyond what the policy tag already allows.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadOnlyDiscovery"
        Effect = "Allow"
        Action = [
          "tag:GetResources",
          "ec2:DescribeInstances",
          "rds:DescribeDBInstances"
        ]
        Resource = "*"
      },
      {
        Sid    = "EC2ScheduleAction"
        Effect = "Allow"
        Action = [
          "ec2:StopInstances",
          "ec2:StartInstances"
        ]
        Resource = "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:instance/*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/${var.schedule_tag_key}" = var.schedule_tag_value
          }
        }
      },
      {
        Sid    = "RDSScheduleAction"
        Effect = "Allow"
        Action = [
          "rds:StopDBInstance",
          "rds:StartDBInstance"
        ]
        Resource = "arn:aws:rds:*:${data.aws_caller_identity.current.account_id}:db:*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/${var.schedule_tag_key}" = var.schedule_tag_value
          }
        }
      },
      {
        Sid    = "Logging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Sid      = "Notify"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = var.enable_sns_notifications ? aws_sns_topic.notifications[0].arn : "*"
      }
    ]
  })
}
