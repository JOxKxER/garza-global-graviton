"""List S3 buckets visible to the configured AWS account."""

from __future__ import annotations

import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


REGION = "us-east-1"


def list_buckets() -> int:
    """Print all S3 buckets returned for the authenticated AWS account."""
    try:
        client = boto3.client("s3", region_name=REGION)
        response = client.list_buckets()
    except NoCredentialsError:
        print(
            "AWS credentials were not found. Configure AWS SSO, an IAM role, "
            "or the AWS CLI first.",
            file=sys.stderr,
        )
        return 2
    except ClientError as error:
        details = error.response.get("Error", {})
        code = details.get("Code", "UnknownError")
        message = details.get("Message", str(error))
        print(f"AWS S3 request failed ({code}): {message}", file=sys.stderr)
        return 1
    except BotoCoreError as error:
        print(f"AWS SDK error: {error}", file=sys.stderr)
        return 1

    buckets = response.get("Buckets", [])
    if not buckets:
        print("No S3 buckets were returned for this AWS account.")
        return 0

    print(f"S3 buckets visible to the account in the {REGION} client context:")
    for bucket in sorted(
        buckets, key=lambda item: item.get("Name", "").lower()
    ):
        print(
            f"- {bucket['Name']} "
            f"(created: {bucket.get('CreationDate', 'unknown')})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(list_buckets())
