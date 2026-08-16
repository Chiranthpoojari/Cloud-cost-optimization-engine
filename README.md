
# Cloud Cost Optimization Engine

> **Policy-driven AWS FinOps automation for reducing non-production infrastructure costs through scheduled resource lifecycle management.**

[![CI](https://github.com/Chiranthpoojari/Cloud-cost-optimization-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Chiranthpoojari/Cloud-cost-optimization-engine/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20EC2%20%7C%20RDS-orange.svg)](https://aws.amazon.com/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-purple.svg)](https://www.terraform.io/)

---

## Executive Summary

The **Cloud Cost Optimization Engine** is a serverless AWS FinOps solution that automatically starts and stops eligible **non-production AWS resources** according to centrally defined tagging policies and operating schedules.

Instead of maintaining hardcoded resource inventories, the platform discovers eligible resources dynamically through the **AWS Resource Groups Tagging API**.

This enables engineering teams to:

* Reduce unnecessary non-production infrastructure runtime
* Automate environment shutdown and startup
* Eliminate manual resource management
* Enforce cost-optimization policies through tags
* Maintain a single reusable Lambda execution engine
* Monitor every automation cycle through CloudWatch
* Optionally notify teams through Amazon SNS
* Provision the complete platform using Terraform

### Business Impact

A typical office-hours policy can reduce eligible non-production runtime from:

**168 hours/week → 65 hours/week**

That represents approximately:

**61.3% less runtime for scheduled resources**

If scheduled non-production resources represent approximately 30% of an organization's AWS bill:

```text
Estimated total-account savings
≈ 30% × 61.3%
≈ 18.4%
```

> **Important:** 18% is an illustrative estimate, not a guaranteed saving. Actual savings depend on resource utilization, workload distribution, instance types, RDS configuration, and the percentage of total spend covered by the policy.

Use the included savings model to calculate the expected impact using actual AWS Cost Explorer data.

---

# Architecture

```text
                         ┌─────────────────────────┐
                         │      AWS EventBridge    │
                         │        Scheduler        │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │      AWS Lambda         │
                         │  Cost Optimization     │
                         │        Engine           │
                         └────────────┬────────────┘
                                      │
                       ┌──────────────▼──────────────┐
                       │ Resource Groups Tagging API │
                       │                            │
                       │ Discover eligible resources│
                       └──────────────┬──────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
             ┌──────▼──────┐                     ┌──────▼──────┐
             │     EC2     │                     │     RDS     │
             │ Start/Stop  │                     │ Start/Stop  │
             └─────────────┘                     └─────────────┘

                                      │
                         ┌────────────▼────────────┐
                         │    CloudWatch Logs      │
                         │ Structured Run Summary  │
                         └────────────┬────────────┘
                                      │
                              ┌───────▼───────┐
                              │      SNS      │
                              │ Notifications │
                              └───────────────┘
```

---

# Key Design Principles

## 1. Tag-driven resource discovery

The engine does not maintain a hardcoded list of EC2 or RDS resources.

Instead, resources opt into automation through tags.

Example:

```text
AutoSchedule = office-hours
Environment  = dev
```

This means teams can create new development infrastructure without modifying the Lambda code.

---

## 2. Policy over inventory

The engine follows a simple principle:

> **Resources declare their scheduling policy; the automation engine enforces it.**

This makes the solution scalable across multiple environments and accounts.

---

## 3. Idempotent operations

The Lambda validates the current resource state before performing an operation.

For example:

```text
STOP request
    ↓
Is resource currently running?
    ├── Yes → Stop
    └── No  → Skip
```

And:

```text
START request
    ↓
Is resource currently stopped?
    ├── Yes → Start
    └── No  → Skip
```

This prevents unnecessary API calls and makes repeated executions safer.

---

# Tagging Contract

Resources must satisfy the defined tagging policy before they become eligible for automation.

### Required tags

```text
AutoSchedule = office-hours
Environment  = dev | staging | qa | test
```

Example EC2 resource:

```text
Name          = payments-api-dev
Environment   = dev
AutoSchedule  = office-hours
Owner         = platform-team
Application   = payments-api
```

The complete tagging contract is documented in:

`policy/tagging_policy.md`

---

# Default Operating Schedule

The reference policy uses:

| Environment    |     Start |      Stop | Days          |
| -------------- | --------: | --------: | ------------- |
| Non-production | 07:00 IST | 20:00 IST | Monday–Friday |

This results in:

```text
13 hours/day × 5 days
= 65 operating hours/week

168 total hours/week
- 65 operating hours
= 103 hours/week avoided
```

Equivalent runtime reduction:

```text
103 / 168 × 100
≈ 61.3%
```

Schedules should be adjusted according to the organization's actual engineering working hours.

---

# Supported AWS Resources

The initial implementation supports:

* Amazon EC2
* Amazon RDS

The architecture is intentionally extensible.

Additional resource types can be introduced through the AWS Resource Groups Tagging API, for example:

```text
elasticache:cluster
redshift:cluster
```

Each service requires its own lifecycle implementation because AWS APIs expose different start/stop semantics.

---

# Technology Stack

| Layer                  | Technology                          |
| ---------------------- | ----------------------------------- |
| Runtime                | Python 3.12                         |
| Compute                | AWS Lambda                          |
| Scheduling             | Amazon EventBridge                  |
| Resource Discovery     | AWS Resource Groups Tagging API     |
| Compute Lifecycle      | Amazon EC2 API                      |
| Database Lifecycle     | Amazon RDS API                      |
| Observability          | Amazon CloudWatch                   |
| Notifications          | Amazon SNS                          |
| Infrastructure as Code | Terraform                           |
| Testing                | Pytest                              |
| CI/CD Validation       | GitHub Actions                      |
| Configuration          | Terraform variables + resource tags |

---

# Repository Structure

```text
cloud-cost-optimization-engine/
│
├── src/
│   └── lambda_function.py
│
├── infrastructure/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── iam.tf
│   ├── lambda.tf
│   ├── eventbridge.tf
│   └── sns.tf
│
├── policy/
│   └── tagging_policy.md
│
├── tests/
│   └── test_lambda_function.py
│
├── scripts/
│   └── estimate_savings.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── requirements.txt
└── README.md
```

---

# Execution Flow

## Scheduled Shutdown

```text
EventBridge
     │
     │ {"action":"stop"}
     ▼
Lambda
     │
     ├── Validate action
     │
     ├── Query tagged resources
     │
     ├── Filter supported resource types
     │
     ├── Validate current state
     │
     ├── Stop eligible resources
     │
     ├── Record successful operations
     │
     ├── Record skipped resources
     │
     └── Record failures
             │
             ▼
       CloudWatch Logs
             │
             ▼
             SNS
```

## Scheduled Startup

The same Lambda is reused with:

```json
{
  "action": "start"
}
```

This avoids maintaining separate implementations for start and stop operations.

---

# Lambda Execution Model

The Lambda receives an action:

```json
{
  "action": "stop"
}
```

or:

```json
{
  "action": "start"
}
```

The execution pipeline is conceptually:

```text
Receive Event
      ↓
Validate Action
      ↓
Discover Tagged Resources
      ↓
Filter Eligible Resources
      ↓
Check Current State
      ↓
Execute Lifecycle Operation
      ↓
Capture Result
      ↓
Emit Structured Summary
      ↓
CloudWatch / SNS
```

---

# Observability

Every execution produces a structured operational summary.

Example:

```json
{
  "action": "stop",
  "resources_discovered": 12,
  "resources_targeted": 8,
  "resources_stopped": 7,
  "resources_skipped": 4,
  "resources_failed": 1,
  "execution_status": "completed"
}
```

This allows operations teams to answer:

* How many resources were discovered?
* How many were eligible?
* How many were actually changed?
* Which resources failed?
* Did the automation execute successfully?
* How frequently are resources being stopped?

CloudWatch Logs can subsequently be used with **CloudWatch Logs Insights** for operational reporting.

---

# Notifications

Amazon SNS can optionally publish execution summaries.

Example notification:

```text
Cloud Cost Optimization Engine

Action: STOP
Environment: Non-Production

Discovered: 12
Targeted:   8
Stopped:    7
Skipped:    4
Failed:     1

Execution status: COMPLETED
```

This gives platform or FinOps teams immediate visibility into scheduled lifecycle operations.

---

# Infrastructure as Code

The entire AWS infrastructure is provisioned through Terraform.

The deployment includes:

* Lambda function
* IAM execution role
* IAM policies
* EventBridge schedules
* CloudWatch logging
* SNS notification infrastructure
* Required AWS configuration

No manual AWS Console configuration should be required for the core deployment.

---

# Security Model

The solution follows a least-privilege approach.

The Lambda execution role requires permissions only for the resources and services it manages.

Conceptually:

```text
Lambda
  │
  ├── Resource Groups Tagging API
  │
  ├── EC2 lifecycle APIs
  │
  ├── RDS lifecycle APIs
  │
  ├── CloudWatch Logs
  │
  └── SNS publishing
```

The engine does **not** require unrestricted administrator access.

For production environments, IAM permissions should be reviewed against the exact AWS API calls used by the implementation.

---

# Deployment

## Prerequisites

Install:

* AWS CLI
* Terraform
* Python 3.12+
* Git

Verify:

```bash
aws --version
terraform version
python --version
git --version
```

Authenticate against the target AWS account:

```bash
aws sts get-caller-identity
```

---

# Deploy with Terraform

Navigate to the infrastructure directory:

```bash
cd infrastructure
```

Initialize Terraform:

```bash
terraform init
```

Review the deployment:

```bash
terraform plan \
  -var="notification_email=you@example.com" \
  -var="aws_region=ap-south-1"
```

Apply:

```bash
terraform apply \
  -var="notification_email=you@example.com" \
  -var="aws_region=ap-south-1"
```

---

# Dry-Run Validation

Before enabling real lifecycle operations, validate the targeting logic using dry-run mode:

```bash
terraform apply \
  -var="dry_run=true"
```

The recommended rollout process is:

```text
Deploy
  ↓
Dry Run
  ↓
Review Targeted Resources
  ↓
Validate Tags
  ↓
Test with Non-Critical Resource
  ↓
Enable Real Operations
  ↓
Monitor CloudWatch
```

This reduces the risk of accidentally stopping an incorrectly tagged resource.

---

# Manual Lambda Test

The Lambda can be invoked manually.

### Stop

```bash
aws lambda invoke \
  --function-name cost-optimizer-engine \
  --payload '{"action":"stop"}' \
  --cli-binary-format raw-in-base64-out \
  out.json
```

Inspect the result:

```bash
cat out.json
```

### Start

```bash
aws lambda invoke \
  --function-name cost-optimizer-engine \
  --payload '{"action":"start"}' \
  --cli-binary-format raw-in-base64-out \
  out.json
```

---

# Testing

The project includes unit tests that mock AWS services.

Run:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

The test suite validates core policy-engine behavior without requiring live AWS infrastructure.

Recommended test coverage includes:

* Resource discovery
* Tag filtering
* Environment filtering
* Start/stop action validation
* Running/stopped state filtering
* EC2 lifecycle operations
* RDS lifecycle operations
* Dry-run behavior
* Failure handling
* Empty resource sets

---

# CI/CD Validation

GitHub Actions validates the project on every push and pull request to `main`.

### Lambda Tests

```text
Install dependencies
        ↓
Run pytest
        ↓
Validate application behavior
```

### Terraform Validation

```text
terraform fmt -check
        ↓
terraform init -backend=false
        ↓
terraform validate
```

The validation pipeline does not require AWS credentials because it performs static Terraform validation rather than deploying infrastructure.

---

# Cost Savings Estimation

The repository includes:

```text
scripts/estimate_savings.py
```

The script can be used to model expected savings based on actual spend.

Conceptually:

```text
Eligible monthly spend
          ×
Avoided runtime percentage
          =
Potential savings
```

For example:

```text
Non-production tagged spend = ₹100,000/month

Runtime reduction = 61.3%

Estimated opportunity
≈ ₹61,300/month
```

Actual savings will vary based on resource characteristics and whether the resource incurs meaningful charges while stopped.

---

# Production Rollout Strategy

A production rollout should follow a controlled adoption model.

### Phase 1 — Development

```text
Deploy Terraform
       ↓
Enable dry-run
       ↓
Validate resource targeting
```

### Phase 2 — Pilot

```text
Select a small set of non-critical resources
       ↓
Apply AutoSchedule tag
       ↓
Observe start/stop behavior
       ↓
Review CloudWatch logs
```

### Phase 3 — Controlled Expansion

```text
Expand to development
       ↓
Expand to QA
       ↓
Expand to staging
```

### Phase 4 — Optimization

```text
Analyze savings
       ↓
Review schedules
       ↓
Identify exceptions
       ↓
Tune policies
```

---

# Failure Handling

The engine should treat individual resource failures independently.

For example:

```text
10 resources targeted

Resource A → SUCCESS
Resource B → SUCCESS
Resource C → FAILED
Resource D → SUCCESS
...
```

A failure on one resource should not prevent eligible resources from being processed.

The execution summary should clearly distinguish:

```text
SUCCESS
SKIPPED
FAILED
```

This makes operational troubleshooting significantly easier.

---

# Safety Considerations

The tagging contract is the primary authorization boundary for lifecycle automation.

Before enabling the scheduler:

* Validate all `AutoSchedule` tags
* Verify environment tags
* Test in dry-run mode
* Start with non-critical resources
* Confirm CloudWatch logging
* Confirm SNS notifications
* Review IAM permissions
* Establish resource exceptions where required

Production resources should **not** opt into the policy unless explicitly intended.

---

# Extensibility

The architecture is designed to evolve beyond EC2 and RDS.

## Additional AWS Services

Potential extensions include:

```text
ElastiCache
Redshift
ECS
EKS node groups
SageMaker
Other taggable resources
```

Each integration should implement the appropriate AWS lifecycle operations and state validation.

---

## Multiple Scheduling Policies

The current policy:

```text
AutoSchedule=office-hours
```

can be extended:

```text
AutoSchedule=office-hours
AutoSchedule=extended-hours
AutoSchedule=weekdays-only
AutoSchedule=qa-hours
```

This allows different teams and environments to use different operating windows without changing the core engine.

---

# Multi-Account Architecture

For larger organizations, the same concept can be extended across multiple AWS accounts.

Example:

```text
                    AWS Organization
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       Dev Account      QA Account      Staging Account
          │                │                │
       Lambda            Lambda           Lambda
          │                │                │
       Resources        Resources        Resources
```

A future centralized architecture could use a dedicated FinOps/platform account to coordinate policies across member accounts.

---

# Future Roadmap

### v1 — Core Automation

* [x] Tag-based resource discovery
* [x] EC2 lifecycle automation
* [x] RDS lifecycle automation
* [x] EventBridge scheduling
* [x] Terraform deployment
* [x] CloudWatch logging
* [x] SNS notifications
* [x] Unit testing

### v2 — Operational Intelligence

* [ ] CloudWatch dashboard
* [ ] Cost Explorer integration
* [ ] Monthly savings reporting
* [ ] Resource-level savings estimation
* [ ] Automated anomaly detection

### v3 — Enterprise FinOps

* [ ] Multi-account support
* [ ] Centralized policy management
* [ ] Approval workflow for new policies
* [ ] Cost allocation reporting
* [ ] Team-level chargeback/showback
* [ ] Web-based FinOps dashboard

---

# Engineering Decisions

## Why Lambda?

The workload is event-driven and periodic, making serverless execution a natural fit.

Benefits:

* No servers to manage
* Pay-per-invocation model
* Native AWS integration
* Easy EventBridge integration
* Automatic scaling

## Why EventBridge?

The engine needs deterministic scheduled execution.

EventBridge provides:

* Cron-based schedules
* Managed scheduling
* Native Lambda integration
* Reliable event delivery

## Why Resource Groups Tagging API?

Hardcoded resource inventories do not scale.

Tag-based discovery allows:

```text
New Resource
     ↓
Apply Tags
     ↓
Automatically Discovered
     ↓
Automatically Managed
```

No Lambda code modification is required.

## Why Terraform?

Terraform provides:

* Reproducible infrastructure
* Version-controlled configuration
* Reviewable infrastructure changes
* Environment consistency
* Automated validation
* Easier disaster recovery

---

# Operational Checklist

Before enabling production scheduling:

* [ ] Terraform plan reviewed
* [ ] IAM permissions reviewed
* [ ] Dry-run successfully completed
* [ ] Resource tagging validated
* [ ] Test EC2 resource verified
* [ ] RDS behavior verified
* [ ] CloudWatch logs confirmed
* [ ] SNS notification confirmed
* [ ] EventBridge schedules verified
* [ ] Exception resources documented
* [ ] Rollback procedure tested

---

# Example Use Case

A development team operates:

```text
10 EC2 instances
3 RDS databases
```

During working hours:

```text
07:00 → Resources started
```

At the end of the working day:

```text
20:00 → Resources stopped
```

During weekends:

```text
Saturday/Sunday → Resources remain stopped
```

The development team does not need to manually manage the infrastructure lifecycle.

The policy engine continuously applies the organization's scheduling policy based on resource tags.

---

# Project Outcomes

This project demonstrates practical implementation of:

* AWS serverless architecture
* Cloud FinOps principles
* Infrastructure as Code
* Event-driven automation
* AWS resource discovery
* IAM least-privilege design
* CloudWatch observability
* SNS notification workflows
* Automated testing
* CI/CD validation
* Production-oriented deployment practices

---

# Contributing

Contributions are welcome.

Recommended workflow:

```bash
git checkout -b feature/<feature-name>
```

Make the required changes, then run:

```bash
pytest tests/ -v
terraform fmt -check
terraform validate
```

Commit:

```bash
git commit -m "feat: add <feature>"
```

Push:

```bash
git push origin feature/<feature-name>
```

Open a pull request against `main`.

---

# License

This project is intended for educational, portfolio, and engineering demonstration purposes.

Before deploying in a production AWS environment, review IAM permissions, resource policies, scheduling requirements, exception handling, and AWS service-specific lifecycle behavior.

---

## Author

**Chiranth Poojari**

Cloud / DevOps Engineering Project

**Focus Areas**

```text
AWS
Terraform
Python
Lambda
EventBridge
Docker
CI/CD
Cloud FinOps
Infrastructure Automation
```

---

> **Built to demonstrate how infrastructure automation can turn cloud cost optimization from a manual operational task into a repeatable, policy-driven engineering capability.**
