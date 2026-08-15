# Tagging policy

The engine never guesses which resources are safe to touch. A resource is
only in scope for automated stop/start if it carries **both** tags below.
No tags = no action, always.

| Tag key       | Required value                          | Purpose                                   |
|---------------|------------------------------------------|--------------------------------------------|
| `AutoSchedule`| `office-hours`                           | Opts the resource into the schedule        |
| `Environment` | one of `dev`, `staging`, `qa`, `test`    | Confirms the resource is non-production    |

Both keys and the non-prod value list are configurable via Terraform
variables (`schedule_tag_key`, `schedule_tag_value`, `env_tag_key`,
`non_prod_envs`), so a team can adapt the policy without touching Lambda
code.

## Why two tags instead of one

A single `Environment=dev` tag is not enough — a team might have a dev
resource that legitimately needs to stay on 24/7 (e.g. a shared dev
database other teams poll). Requiring an explicit `AutoSchedule` opt-in
on top of the environment tag means:

- Nothing is shut down by being merely non-prod.
- Turning scheduling on/off for one resource is a single tag edit, not a
  code change or an exclusion list to maintain.
- The same IAM policy that grants the Lambda `StopInstances`/
  `StartInstances` is itself scoped with an `aws:ResourceTag` condition
  on `AutoSchedule=office-hours` (see `infrastructure/iam.tf`), so even a
  bug in the Lambda's own filtering can't widen the blast radius beyond
  what the tag already authorizes.

## Applying the tags

EC2:
```bash
aws ec2 create-tags --resources i-0123456789abcdef0 \
  --tags Key=AutoSchedule,Value=office-hours Key=Environment,Value=dev
```

RDS:
```bash
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:ap-south-1:111111111111:db:my-dev-db \
  --tags Key=AutoSchedule,Value=office-hours Key=Environment,Value=dev
```

Or via Terraform, on any `aws_instance` / `aws_db_instance` resource:
```hcl
tags = {
  AutoSchedule = "office-hours"
  Environment  = "dev"
}
```
