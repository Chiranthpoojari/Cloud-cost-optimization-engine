variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix used for naming all resources"
  type        = string
  default     = "cost-optimizer"
}

variable "schedule_tag_key" {
  description = "Tag key that opts a resource into the schedule"
  type        = string
  default     = "AutoSchedule"
}

variable "schedule_tag_value" {
  description = "Tag value that opts a resource into the schedule"
  type        = string
  default     = "office-hours"
}

variable "env_tag_key" {
  description = "Tag key used to identify environment"
  type        = string
  default     = "Environment"
}

variable "non_prod_envs" {
  description = "Comma-separated list of Environment tag values treated as non-prod"
  type        = string
  default     = "dev,staging,qa,test"
}

variable "stop_schedule_expression" {
  description = "EventBridge schedule expression for shutting resources down (cron is UTC)"
  type        = string
  default     = "cron(30 14 ? * MON-FRI *)" # 20:00 IST Mon-Fri
}

variable "start_schedule_expression" {
  description = "EventBridge schedule expression for starting resources back up (cron is UTC)"
  type        = string
  default     = "cron(30 1 ? * MON-FRI *)" # 07:00 IST Mon-Fri
}

variable "dry_run" {
  description = "If true, Lambda logs intended actions without calling stop/start APIs"
  type        = bool
  default     = false
}

variable "enable_sns_notifications" {
  description = "Whether to create an SNS topic and notify on each run"
  type        = bool
  default     = true
}

variable "notification_email" {
  description = "Email address subscribed to the SNS topic (leave empty to skip subscription)"
  type        = string
  default     = ""
}
