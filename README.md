# Cloud cost optimization engine

![CI](https://github.com/<your-github-username>/<repo-name>/actions/workflows/ci.yml/badge.svg)

Scheduled shutdown/restart of idle non-production AWS resources, driven
entirely by tags — no hardcoded resource lists to maintain.

**Stack:** Python 3.12 (Lambda) · Amazon EventBridge (Scheduler) · Resource
Groups Tagging API · Terraform (IaC) · CloudWatch Logs + SNS (observability)

## Problem

Non-prod environments (dev, staging, QA) are typically provisioned like
production but run 24/7 even though they're only used during working
hours. That idle overnight/weekend runtime is pure waste.

## Approach

1. Every eligible EC2/RDS resource is tagged `AutoSchedule=office-hours`
   plus `Environment=<dev|staging|qa|test>`.
2. Two EventBridge rules fire on a cron schedule — one at end-of-day
   (`stop`), one at start-of-day (`start`) — invoking the same Lambda
   with a different payload.
3. The Lambda queries the **Resource Groups Tagging API** for everything
   matching the policy, filters to the correct pre-action state (only
   stop what's running, only start what's stopped), and calls the
   relevant EC2/RDS stop or start API.
4. Every run logs a structured summary to CloudWatch and optionally
   publishes it to SNS.

Full tagging contract: [`policy/tagging_policy.md`](policy/tagging_policy.md).

## Why savings land around 18%

With the default schedule (07:00–20:00 IST, Mon–Fri), tagged resources
run **65 of 168 hours/week** — a 61% cut in their own runtime. Applied
only to the slice of the bill that's tagged non-prod compute (commonly
25–35% of total spend in an account with shared prod/non-prod billing),
that works out to roughly:

```
savings % of total bill ≈ tagged_fraction_of_bill × 0.613
                         ≈ 0.30 × 0.613 ≈ 18%
```

Run `scripts/estimate_savings.py` against your own numbers (from AWS
Cost Explorer, filtered to the `AutoSchedule` tag) to get your actual
figure rather than relying on the rule of thumb.

## Project layout

```
src/lambda_function.py        Lambda handler — the whole policy engine
infrastructure/                Terraform: Lambda, IAM, EventBridge, SNS
policy/tagging_policy.md       The tagging contract, explained
tests/test_lambda_function.py  Unit tests (mocked boto3, no AWS needed)
scripts/estimate_savings.py    Savings modeling script
.github/workflows/ci.yml       CI: pytest + terraform fmt/validate
```

## Deploy it

```bash
cd infrastructure
terraform init
terraform plan \
  -var="notification_email=you@example.com" \
  -var="aws_region=ap-south-1"
terraform apply
```

Defaults deploy in dry-run **off** (real stop/start calls). To watch it
run without touching real resources first:

```bash
terraform apply -var="dry_run=true"
```

Then tag a throwaway EC2 instance and invoke the function manually to
confirm targeting before trusting the schedule:

```bash
aws lambda invoke --function-name cost-optimizer-engine \
  --payload '{"action":"stop"}' --cli-binary-format raw-in-base64-out out.json
cat out.json
```

## Run the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Continuous integration

`.github/workflows/ci.yml` runs on every push/PR to `main` with two jobs:

- **test-lambda** — installs `requirements.txt` and runs `pytest tests/ -v`.
- **validate-terraform** — `terraform fmt -check`, then `init -backend=false`
  and `terraform validate`. No AWS credentials or backend needed since it
  only checks syntax and formatting, not a real plan.

After pushing this repo to GitHub, replace `<your-github-username>/<repo-name>`
in the badge URL above with your actual repo path.

## Extending it

- **More services**: `ResourceTypeFilters` in `find_target_resources()`
  accepts any Resource Groups Tagging API type (`elasticache:cluster`,
  `redshift:cluster`, etc.) — add the type and a matching stop/start
  branch.
- **Per-team schedules**: add a second `AutoSchedule` value (e.g.
  `extended-hours`) and a third pair of EventBridge rules.
- **Cost dashboard**: the CloudWatch log summary is structured JSON —
  feed it into a CloudWatch Logs Insights query or a small QuickSight
  dashboard to track cumulative savings over time instead of just
  estimating them upfront.
