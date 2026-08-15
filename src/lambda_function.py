"""
Cloud Cost Optimization Engine
-------------------------------
Lambda handler that stops or starts non-production AWS resources based on
policy-driven tags. Triggered on a schedule by two EventBridge rules
(one for "stop", one for "start") that pass {"action": "stop"} or
{"action": "start"} as the event payload.

Policy:
  A resource is IN SCOPE if it carries both:
    - <SCHEDULE_TAG_KEY> = <SCHEDULE_TAG_VALUE>   (default: AutoSchedule=office-hours)
    - <ENV_TAG_KEY> in <NON_PROD_ENVS>            (default: Environment in dev,staging,qa,test)

  Resources without both tags are never touched — this makes the blast
  radius explicit and opt-in rather than opt-out.

Supported services: EC2 instances, RDS instances.
Discovery uses the Resource Groups Tagging API so the same tag policy
applies uniformly across services without per-service tag scanning.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---- Policy configuration (overridable via Lambda environment variables) ----
SCHEDULE_TAG_KEY = os.environ.get("SCHEDULE_TAG_KEY", "AutoSchedule")
SCHEDULE_TAG_VALUE = os.environ.get("SCHEDULE_TAG_VALUE", "office-hours")
ENV_TAG_KEY = os.environ.get("ENV_TAG_KEY", "Environment")
NON_PROD_ENVS = [e.strip() for e in os.environ.get("NON_PROD_ENVS", "dev,staging,qa,test").split(",") if e.strip()]
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")  # optional
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

tagging_client = boto3.client("resourcegroupstaggingapi")
ec2_client = boto3.client("ec2")
rds_client = boto3.client("rds")
sns_client = boto3.client("sns")


def find_target_resources():
    """
    Returns {"ec2": [instance_ids], "rds": [db_instance_identifiers]}
    for every resource matching the schedule + non-prod tag policy.
    """
    targets = {"ec2": [], "rds": []}
    paginator = tagging_client.get_paginator("get_resources")
    page_iterator = paginator.paginate(
        ResourceTypeFilters=["ec2:instance", "rds:db"],
        TagFilters=[
            {"Key": SCHEDULE_TAG_KEY, "Values": [SCHEDULE_TAG_VALUE]},
            {"Key": ENV_TAG_KEY, "Values": NON_PROD_ENVS},
        ],
    )

    for page in page_iterator:
        for mapping in page.get("ResourceTagMappingList", []):
            arn = mapping["ResourceARN"]
            # arn:aws:ec2:region:account:instance/i-0123456789abcdef0  (slash-delimited resource)
            # arn:aws:rds:region:account:db:my-db-identifier           (colon-delimited resource)
            # split with maxsplit=5 so a colon-delimited resource id doesn't get chopped
            parts = arn.split(":", 5)
            service = parts[2]
            resource_part = parts[5]

            if service == "ec2" and resource_part.startswith("instance/"):
                targets["ec2"].append(resource_part.split("/", 1)[1])
            elif service == "rds" and resource_part.startswith("db:"):
                targets["rds"].append(resource_part.split(":", 1)[1])

    return targets


def filter_ec2_by_state(instance_ids, desired_current_state):
    """Only act on instances actually in the expected pre-action state."""
    if not instance_ids:
        return []
    matched = []
    paginator = ec2_client.get_paginator("describe_instances")
    for page in paginator.paginate(InstanceIds=instance_ids):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] == desired_current_state:
                    matched.append(instance["InstanceId"])
    return matched


def act_on_ec2(instance_ids, action):
    if not instance_ids:
        return []
    if DRY_RUN:
        logger.info("[DRY_RUN] Would %s EC2 instances: %s", action, instance_ids)
        return instance_ids
    try:
        if action == "stop":
            ec2_client.stop_instances(InstanceIds=instance_ids)
        else:
            ec2_client.start_instances(InstanceIds=instance_ids)
        return instance_ids
    except ClientError as exc:
        logger.error("EC2 %s failed for %s: %s", action, instance_ids, exc)
        return []


def act_on_rds(db_ids, action):
    acted = []
    for db_id in db_ids:
        if DRY_RUN:
            logger.info("[DRY_RUN] Would %s RDS instance: %s", action, db_id)
            acted.append(db_id)
            continue
        try:
            if action == "stop":
                rds_client.stop_db_instance(DBInstanceIdentifier=db_id)
            else:
                rds_client.start_db_instance(DBInstanceIdentifier=db_id)
            acted.append(db_id)
        except ClientError as exc:
            # Commonly InvalidDBInstanceState if it's already mid-transition —
            # log and continue rather than failing the whole batch.
            logger.warning("RDS %s skipped for %s: %s", action, db_id, exc)
    return acted


def notify(summary):
    if not SNS_TOPIC_ARN:
        return
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Cost optimizer: {summary['action']} run complete",
            Message=json.dumps(summary, indent=2),
        )
    except ClientError as exc:
        logger.error("SNS publish failed: %s", exc)


def handler(event, context):
    action = event.get("action")
    if action not in ("stop", "start"):
        raise ValueError(f"event['action'] must be 'stop' or 'start', got: {action!r}")

    targets = find_target_resources()

    if action == "stop":
        ec2_candidates = filter_ec2_by_state(targets["ec2"], "running")
    else:
        ec2_candidates = filter_ec2_by_state(targets["ec2"], "stopped")

    ec2_result = act_on_ec2(ec2_candidates, action)
    rds_result = act_on_rds(targets["rds"], action)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "dry_run": DRY_RUN,
        "policy": {
            "tag": f"{SCHEDULE_TAG_KEY}={SCHEDULE_TAG_VALUE}",
            "non_prod_envs": NON_PROD_ENVS,
        },
        "ec2_matched": targets["ec2"],
        "ec2_acted_on": ec2_result,
        "rds_matched": targets["rds"],
        "rds_acted_on": rds_result,
    }

    logger.info(json.dumps(summary))
    notify(summary)

    return summary
