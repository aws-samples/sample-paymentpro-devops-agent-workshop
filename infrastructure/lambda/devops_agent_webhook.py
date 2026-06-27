"""
Lambda function that forwards CloudWatch Alarm events to AWS DevOps Agent webhook.
Triggered when any PaymentPro alarm enters ALARM state.

The webhook URL is configured as a plain environment variable (URLs are not
secrets). The HMAC shared secret is read from AWS Secrets Manager at invocation
time using the ARN supplied via the `WEBHOOK_SECRET_ARN` environment variable.
The fetched value is cached in module-level state for the lifetime of the
warm Lambda execution context to avoid per-invocation Secrets Manager calls.
"""

import json
import os
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
from datetime import datetime

import boto3


WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_SECRET_ARN = os.environ.get("WEBHOOK_SECRET_ARN", "")

# Module-level cache (persists across warm invocations).
_secrets_client = None
_cached_secret_value = None


def _get_webhook_secret() -> str:
    """Fetch the webhook HMAC secret from Secrets Manager, with warm-Lambda caching.

    Returns an empty string when the ARN is not configured, which signals the
    caller to short-circuit (matches the behaviour when the stack is deployed
    without a webhook).
    """
    global _secrets_client, _cached_secret_value

    if not WEBHOOK_SECRET_ARN:
        return ""

    if _cached_secret_value is not None:
        return _cached_secret_value

    if _secrets_client is None:
        _secrets_client = boto3.client("secretsmanager")

    response = _secrets_client.get_secret_value(SecretId=WEBHOOK_SECRET_ARN)
    _cached_secret_value = response.get("SecretString", "")
    return _cached_secret_value


def lambda_handler(event, context):
    """
    Triggered by CloudWatch Alarm state change (Lambda action).
    Signs payload with HMAC and sends to DevOps Agent webhook.
    """
    print(f"Received event: {json.dumps(event)}")

    webhook_secret = _get_webhook_secret()
    if not WEBHOOK_URL or not webhook_secret:
        print("ERROR: WEBHOOK_URL and WEBHOOK_SECRET_ARN must both be configured")
        return {"statusCode": 500, "body": "Missing webhook configuration"}

    try:
        # Handle SNS wrapper (alarms come via SNS)
        if "Records" in event:
            # SNS message
            sns_message = json.loads(event["Records"][0]["Sns"]["Message"])
            alarm_name = sns_message.get("AlarmName", "Unknown")
            alarm_description = sns_message.get("AlarmDescription", "")
            new_state = sns_message.get("NewStateValue", "ALARM")
            reason = sns_message.get("NewStateReason", "")
            timestamp = sns_message.get("StateChangeTime", datetime.utcnow().isoformat() + "Z")
            region = sns_message.get("Region", "us-east-1")
            account_id = sns_message.get("AWSAccountId", "123456789012")
            metrics = []
        else:
            # Direct Lambda invocation (alarm action or test)
            alarm_data = event.get("alarmData", {})
            alarm_name = alarm_data.get("alarmName", event.get("detail", {}).get("alarmName", "Unknown"))
            alarm_description = alarm_data.get("configuration", {}).get("description", "")
            state = alarm_data.get("state", {})
            new_state = state.get("value", "ALARM")
            reason = state.get("reason", "")
            timestamp = state.get("timestamp", datetime.utcnow().isoformat() + "Z")
            region = event.get("region", "us-east-1")
            account_id = event.get("accountId", "123456789012")
            metrics = alarm_data.get("configuration", {}).get("metrics", [])

        # Only trigger investigation for ALARM state
        if new_state != "ALARM":
            print(f"State is {new_state}, not ALARM. Skipping.")
            return {"statusCode": 200, "body": "Not in ALARM state"}

        # Extract metric info
        metric_info = ""
        if metrics:
            metric = metrics[0].get("metricStat", {}).get("metric", {})
            metric_name = metric.get("name", "")
            namespace = metric.get("namespace", "")
            dimensions = metric.get("dimensions", {})
            metric_info = f"Metric: {namespace}/{metric_name}"
            if dimensions:
                metric_info += f" Dimensions: {json.dumps(dimensions)}"

        # Build description
        description = (
            f"CloudWatch Alarm: {alarm_name}\n"
            f"Account: {account_id} | Region: {region}\n"
            f"State: {new_state}\n"
            f"Reason: {reason}\n"
        )
        if alarm_description:
            description += f"Description: {alarm_description}\n"
        if metric_info:
            description += f"{metric_info}\n"

        # Create DevOps Agent webhook payload
        payload = {
            "eventType": "incident",
            "incidentId": f"{alarm_name}-{timestamp}",
            "action": "created",
            "priority": "HIGH",
            "title": f"CloudWatch Alarm: {alarm_name}",
            "description": description,
            "timestamp": timestamp,
            "service": alarm_name.replace("PaymentPro-", ""),
            "data": {
                "metadata": {
                    "alarmName": alarm_name,
                    "region": region,
                    "accountId": account_id,
                    "newState": new_state,
                    "reason": reason,
                    "alarmArn": event.get("alarmArn", ""),
                    "metrics": metrics,
                }
            },
        }

        payload_json = json.dumps(payload)
        event_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Generate HMAC-SHA256 signature
        signature_string = f"{event_timestamp}:{payload_json}"
        signature = hmac.new(
            webhook_secret.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.b64encode(signature).decode("utf-8")

        # Send webhook request
        headers = {
            "Content-Type": "application/json",
            "x-amzn-event-timestamp": event_timestamp,
            "x-amzn-event-signature": signature_b64,
        }

        req = urllib.request.Request(
            WEBHOOK_URL,
            data=payload_json.encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            resp_body = response.read().decode("utf-8")
            print(f"Webhook response: {response.status} - {resp_body}")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Investigation triggered",
                    "alarm": alarm_name,
                    "webhookStatus": response.status,
                }),
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        print(f"Webhook HTTP Error {e.code}: {error_body}")
        return {"statusCode": e.code, "body": error_body}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise
