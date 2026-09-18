"""Create the Graviton Forge AWS Data Exchange data set."""

from __future__ import annotations

import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


DATA_SET_NAME = "Graviton Forge"
DATA_SET_DESCRIPTION = (
    "Public-domain normalized datasets packaged for downstream cloud storage "
    "and AWS Data Exchange distribution."
)


def create_data_set() -> int:
    """Create the S3 snapshot data set and print its identifiers.

    Returns zero on success and a non-zero status on failure so the script can
    be used from CI, deployment scripts, or a scheduled job.
    """
    try:
        client = boto3.client("dataexchange", region_name="us-east-1")
        response = client.create_data_set(
            AssetType="S3_SNAPSHOT",
            Description=DATA_SET_DESCRIPTION,
            Name=DATA_SET_NAME,
        )
    except NoCredentialsError:
        print(
            "AWS credentials were not found. Configure an IAM role, AWS SSO, "
            "or the AWS CLI before running this script.",
            file=sys.stderr,
        )
        return 2
    except ClientError as error:
        details = error.response.get("Error", {})
        code = details.get("Code", "UnknownError")
        message = details.get("Message", str(error))
        print(
            f"Data Exchange request failed ({code}): {message}",
            file=sys.stderr,
        )
        return 1
    except BotoCoreError as error:
        print(f"AWS SDK error: {error}", file=sys.stderr)
        return 1
    except (KeyError, TypeError) as error:
        print(f"Unexpected AWS response: {error}", file=sys.stderr)
        return 1

    print("Successfully created Data Exchange data set.")
    print(f"Data Set ID: {response['Id']}")
    print(f"ARN: {response['Arn']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(create_data_set())
