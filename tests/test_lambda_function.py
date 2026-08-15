"""
Unit tests for lambda_function.py.

Boto3 clients are mocked directly (module-level attribute patching) rather
than hitting real AWS or requiring moto, so these run anywhere with just
boto3 + pytest installed.

Run with:  pytest tests/ -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import lambda_function as lf  # noqa: E402


def make_paginator(pages):
    paginator = MagicMock()
    paginator.paginate.return_value = pages
    return paginator


class TestFindTargetResources:
    def test_splits_ec2_and_rds_by_arn(self):
        pages = [
            {
                "ResourceTagMappingList": [
                    {"ResourceARN": "arn:aws:ec2:ap-south-1:111111111111:instance/i-0abc123"},
                    {"ResourceARN": "arn:aws:rds:ap-south-1:111111111111:db:my-dev-db"},
                ]
            }
        ]
        with patch.object(lf.tagging_client, "get_paginator", return_value=make_paginator(pages)):
            targets = lf.find_target_resources()

        assert targets["ec2"] == ["i-0abc123"]
        assert targets["rds"] == ["my-dev-db"]

    def test_empty_result(self):
        with patch.object(lf.tagging_client, "get_paginator", return_value=make_paginator([{"ResourceTagMappingList": []}])):
            targets = lf.find_target_resources()
        assert targets == {"ec2": [], "rds": []}


class TestFilterEc2ByState:
    def test_only_returns_matching_state(self):
        pages = [
            {
                "Reservations": [
                    {
                        "Instances": [
                            {"InstanceId": "i-1", "State": {"Name": "running"}},
                            {"InstanceId": "i-2", "State": {"Name": "stopped"}},
                        ]
                    }
                ]
            }
        ]
        with patch.object(lf.ec2_client, "get_paginator", return_value=make_paginator(pages)):
            result = lf.filter_ec2_by_state(["i-1", "i-2"], "running")
        assert result == ["i-1"]

    def test_empty_input_short_circuits(self):
        with patch.object(lf.ec2_client, "get_paginator") as mock_paginator:
            result = lf.filter_ec2_by_state([], "running")
        assert result == []
        mock_paginator.assert_not_called()


class TestActOnEc2:
    def test_dry_run_skips_api_call(self):
        with patch.object(lf, "DRY_RUN", True), patch.object(lf.ec2_client, "stop_instances") as mock_stop:
            result = lf.act_on_ec2(["i-1"], "stop")
        mock_stop.assert_not_called()
        assert result == ["i-1"]

    def test_live_run_calls_stop(self):
        with patch.object(lf, "DRY_RUN", False), patch.object(lf.ec2_client, "stop_instances") as mock_stop:
            result = lf.act_on_ec2(["i-1", "i-2"], "stop")
        mock_stop.assert_called_once_with(InstanceIds=["i-1", "i-2"])
        assert result == ["i-1", "i-2"]


class TestActOnRds:
    def test_continues_after_one_failure(self):
        from botocore.exceptions import ClientError

        error = ClientError({"Error": {"Code": "InvalidDBInstanceState", "Message": "busy"}}, "StopDBInstance")
        with patch.object(lf, "DRY_RUN", False), patch.object(
            lf.rds_client, "stop_db_instance", side_effect=[error, None]
        ):
            result = lf.act_on_rds(["db-1", "db-2"], "stop")
        assert result == ["db-2"]


class TestHandler:
    def test_rejects_unknown_action(self):
        with pytest.raises(ValueError):
            lf.handler({"action": "pause"}, None)

    def test_stop_action_end_to_end(self):
        targets = {"ec2": ["i-1"], "rds": ["db-1"]}
        with patch.object(lf, "find_target_resources", return_value=targets), patch.object(
            lf, "filter_ec2_by_state", return_value=["i-1"]
        ), patch.object(lf, "act_on_ec2", return_value=["i-1"]) as mock_ec2, patch.object(
            lf, "act_on_rds", return_value=["db-1"]
        ) as mock_rds, patch.object(
            lf, "notify"
        ) as mock_notify:
            result = lf.handler({"action": "stop"}, None)

        mock_ec2.assert_called_once_with(["i-1"], "stop")
        mock_rds.assert_called_once_with(["db-1"], "stop")
        mock_notify.assert_called_once()
        assert result["action"] == "stop"
        assert result["ec2_acted_on"] == ["i-1"]
        assert result["rds_acted_on"] == ["db-1"]
