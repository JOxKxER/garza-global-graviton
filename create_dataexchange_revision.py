"""Import an S3 object into an AWS Data Exchange revision and finalize it."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


DATA_SET_ID = "9e62c133d48a7936aaa7b6080c528801"
DEFAULT_REGION = "us-east-1"
DEFAULT_POLL_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_LOCAL_FILE = (
    "dataset_revisions/revision=20260828T210255Z/"
    "observed_date=2026-08-28/data.ndjson.gz"
)
LOGGER = logging.getLogger("dataexchange_revision")


def describe_client_error(error: ClientError) -> tuple[str, str]:
    """Return a stable error code and message from a botocore exception."""
    details = error.response.get("Error", {})
    return (
        details.get("Code", "UnknownError"),
        details.get("Message", str(error)),
    )


def get_principal_arn(sts_client: object) -> str:
    """Return the ARN or fallback identifier for the active AWS principal."""
    identity = sts_client.get_caller_identity()
    return identity.get("Arn", identity.get("UserId", "unknown"))


def report_principal(sts_client: object) -> str:
    """Print and log the AWS principal used for the S3 checks."""
    principal = get_principal_arn(sts_client)
    print(f"AWS principal: {principal}")
    LOGGER.info("Verifying S3 access for principal %s", principal)
    return principal


def is_missing_object(error: ClientError) -> bool:
    """Return whether an S3 error identifies a missing object."""
    code, _ = describe_client_error(error)
    status_code = error.response.get("ResponseMetadata", {}).get(
        "HTTPStatusCode"
    )
    return code in {"NoSuchKey", "NotFound", "404"} or status_code == 404


def verify_s3_source(
    bucket: str,
    key: str,
    region: str,
    local_file: str,
) -> bool:
    """Verify S3 access and upload the local object when it is missing."""
    s3_client = boto3.client("s3", region_name=region)
    sts_client = boto3.client("sts", region_name=region)

    try:
        report_principal(sts_client)

        s3_client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
        LOGGER.info("Confirmed effective s3:ListBucket access for %s", bucket)

        try:
            s3_client.head_object(Bucket=bucket, Key=key)
        except ClientError as error:
            if not is_missing_object(error):
                raise
            local_path = os.path.abspath(local_file)
            if not os.path.isfile(local_path):
                LOGGER.error(
                    "S3 object is missing and local fallback does not exist: "
                    "%s",
                    local_path,
                )
                return False
            LOGGER.warning(
                "S3 object is missing; uploading local file %s to s3://%s/%s",
                local_path,
                bucket,
                key,
            )
            s3_client.upload_file(local_path, bucket, key)
            LOGGER.info("Uploaded local fallback to s3://%s/%s", bucket, key)
            s3_client.head_object(Bucket=bucket, Key=key)
        LOGGER.info(
            "Confirmed effective s3:GetObject access for s3://%s/%s",
            bucket,
            key,
        )
        print(f"Confirmed S3 bucket and object access: s3://{bucket}/{key}")
        return True
    except ClientError as error:
        code, message = describe_client_error(error)
        if code in {"NoSuchBucket", "NoSuchKey", "NotFound", "404"}:
            LOGGER.error(
                "S3 resource not found for s3://%s/%s (%s): %s",
                bucket,
                key,
                code,
                message,
            )
        elif code in {"AccessDenied", "AllAccessDisabled"}:
            LOGGER.error(
                "S3 permission check failed for s3://%s/%s (%s): %s. "
                "The caller needs s3:ListBucket on the bucket and "
                "s3:GetObject on the object. Upload recovery also needs "
                "s3:PutObject.",
                bucket,
                key,
                code,
                message,
            )
        else:
            LOGGER.error(
                "S3 preflight failed for s3://%s/%s (%s): %s",
                bucket,
                key,
                code,
                message,
            )
        return False


def create_and_finalize_revision(
    bucket: str,
    key: str,
    dataset_id: str = DATA_SET_ID,
    local_file: str = DEFAULT_LOCAL_FILE,
    region: str = DEFAULT_REGION,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> int:
    """Create a revision, import one S3 object, and finalize the revision."""
    client = boto3.client("dataexchange", region_name=region)
    revision_id = ""
    job_id = ""

    try:
        if not verify_s3_source(bucket, key, region, local_file):
            return 1

        revision = client.create_revision(DataSetId=dataset_id)
        revision_id = revision["Id"]
        print(f"Created revision: {revision_id}")

        job = client.create_job(
            Type="IMPORT_ASSETS_FROM_S3",
            Details={
                "ImportAssetsFromS3": {
                    "DataSetId": dataset_id,
                    "RevisionId": revision_id,
                    "AssetSources": [
                        {
                            "Bucket": bucket,
                            "Key": key,
                        }
                    ],
                }
            },
        )
        job_id = job["Id"]
        print(f"Created import job: {job_id}")

        client.start_job(JobId=job_id)
        print("Import job started; waiting for completion...")

        deadline = time.monotonic() + timeout_seconds
        while True:
            job_status = client.get_job(JobId=job_id)
            state = job_status["State"]
            print(f"Import job state: {state}")

            if state == "COMPLETED":
                break
            if state in {"ERROR", "CANCELLED", "CANCELED"}:
                details = job_status.get(
                    "Errors", job_status.get("Details", "")
                )
                raise RuntimeError(f"Import job ended in {state}: {details}")
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Import job {job_id} did not finish within "
                    f"{timeout_seconds} seconds"
                )
            time.sleep(poll_seconds)

        client.update_revision(
            DataSetId=dataset_id,
            RevisionId=revision_id,
            Comment=f"Imported s3://{bucket}/{key}",
            Finalized=True,
        )
        print("Revision finalized successfully.")
        print(f"Data Set ID: {dataset_id}")
        print(f"Revision ID: {revision_id}")
        return 0

    except NoCredentialsError:
        print(
            "AWS credentials were not found. Configure AWS SSO, an IAM role, "
            "or the AWS CLI before running this script.",
            file=sys.stderr,
        )
        return 2
    except ClientError as error:
        code, message = describe_client_error(error)
        if code == "RESOURCE_NOT_FOUND_EXCEPTION":
            LOGGER.error(
                "AWS Data Exchange resource not found. DataSetId=%s, "
                "RevisionId=%s, JobId=%s. Details: %s",
                dataset_id,
                revision_id or "not-created",
                job_id or "not-created",
                message,
            )
        print(
            f"AWS request failed ({code}): {message}",
            file=sys.stderr,
        )
        if revision_id:
            print(
                f"Revision {revision_id} was created but not finalized. "
                "Inspect or clean it up in AWS Data Exchange.",
                file=sys.stderr,
            )
        return 1
    except (BotoCoreError, RuntimeError, TimeoutError, KeyError) as error:
        print(f"Revision workflow failed: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import an S3 object into an AWS Data Exchange revision."
    )
    parser.add_argument(
        "--dataset-id",
        help="AWS Data Exchange dataset ID, or provide dataset_id "
        "in --config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config file containing dataset_id, bucket, "
        "and key.",
    )
    parser.add_argument(
        "--bucket",
        default=os.environ.get("S3_BUCKET"),
        help="Source S3 bucket, or set S3_BUCKET.",
    )
    parser.add_argument(
        "--key",
        default=os.environ.get("S3_KEY"),
        help="Source S3 object key, or set S3_KEY.",
    )
    parser.add_argument(
        "--local-file",
        default=os.environ.get("LOCAL_FILE"),
        help="Local fallback file to upload when the S3 object is missing.",
    )
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument(
        "--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS
    )
    parser.add_argument(
        "--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS
    )
    return parser


def load_config(path: Path | None) -> dict[str, str]:
    """Load string settings from an optional JSON configuration file."""
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("configuration root must be a JSON object")
    return {
        str(key): str(value)
        for key, value in config.items()
        if value is not None
    }


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    try:
        config = load_config(args.config)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not load configuration: {error}", file=sys.stderr)
        return 2

    dataset_id = args.dataset_id or config.get("dataset_id") or DATA_SET_ID
    bucket = args.bucket or config.get("bucket")
    key = args.key or config.get("key")
    local_file = args.local_file or config.get(
        "local_file", DEFAULT_LOCAL_FILE
    )

    if not bucket or not key:
        print(
            "Both --bucket and --key are required, or set "
            "S3_BUCKET and S3_KEY.",
            file=sys.stderr,
        )
        return 2
    if args.poll_seconds < 1 or args.timeout_seconds < 1:
        print("Polling and timeout values must be positive.", file=sys.stderr)
        return 2
    return create_and_finalize_revision(
        bucket=bucket,
        key=key,
        dataset_id=dataset_id,
        local_file=local_file,
        region=args.region,
        poll_seconds=args.poll_seconds,
        timeout_seconds=args.timeout_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
