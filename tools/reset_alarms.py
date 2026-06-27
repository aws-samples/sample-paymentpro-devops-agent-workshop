"""Reset all PaymentPro alarms to OK state.

Uses the ambient AWS credentials (env vars or default profile).
Override the region with AWS_DEFAULT_REGION if not us-east-1.
"""
import os
import boto3

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

cw = boto3.client("cloudwatch", region_name=REGION)

paginator = cw.get_paginator("describe_alarms")
alarms = []
for page in paginator.paginate(AlarmNamePrefix="PaymentPro"):
    alarms.extend(a["AlarmName"] for a in page.get("MetricAlarms", []))

print(f"Resetting {len(alarms)} alarms to OK in {REGION}...")
for alarm in alarms:
    cw.set_alarm_state(
        AlarmName=alarm,
        StateValue="OK",
        StateReason="Manual reset",
    )
    print(f"  reset: {alarm}")
print("Done.")
