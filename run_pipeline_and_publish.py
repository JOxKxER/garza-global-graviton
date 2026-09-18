"""Run the public pipeline and publish its revision to AWS Data Exchange."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from public_data_pipeline import PipelineConfig, run_pipeline


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "pipeline.json"
DEFAULT_BUCKET = "garza-global-graviton-storage-01"
DEFAULT_DATASET_ID = "d90878cf531fe68aa00f719e4b55143c"
DEFAULT_REGION = "us-east-1"
DEFAULT_PREFIX = "dataset-revisions"
DEFAULT_POLL_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 1800
LOGGER = logging.getLogger("run_pipeline_and_publish")


def describe_error(error: ClientError) -> tuple[str, str]:
    """Extract a stable AWS error code and message."""
    details = error.response.get("Error", {})
    return (
        details.get("Code", "UnknownError"),
        details.get("Message", str(error)),
    )


def find_partition_files(
    revision_dir: Path, manifest: dict[str, Any]
) -> list[tuple[Path, str]]:
    """Resolve manifest partition paths and destination-relative paths."""
    partitions = manifest.get("partitions", [])
    if not isinstance(partitions, list) or not partitions:
        raise RuntimeError("Pipeline produced no export partitions")

    resolved: list[tuple[Path, str]] = []
    for partition in partitions:
        relative_path = (
            partition.get("path") if isinstance(partition, dict) else None
        )
        if not relative_path:
            raise RuntimeError(
                "Revision manifest contains an invalid partition path"
            )
        local_path = revision_dir / Path(relative_path)
        if local_path.suffixes[-2:] != [".ndjson", ".gz"]:
            raise RuntimeError(
                f"Partition is not compressed NDJSON: {local_path}"
            )
        if not local_path.is_file():
            raise FileNotFoundError(
                f"Manifest partition does not exist: {local_path}"
            )
        resolved.append((local_path, str(relative_path).replace("\\", "/")))
    return resolved


def upload_revision(
    s3_client: Any,
    bucket: str,
    prefix: str,
    revision: str,
    revision_dir: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Upload partitions beneath their timestamped revision prefix."""
    object_keys: list[str] = []
    partition_files = find_partition_files(revision_dir, manifest)
    for local_path, relative_path in partition_files:
        object_key = f"{prefix.strip('/')}/revision={revision}/{relative_path}"
        LOGGER.info(
            "Uploading %s to s3://%s/%s", local_path, bucket, object_key
        )
        s3_client.upload_file(str(local_path), bucket, object_key)
        object_keys.append(object_key)
    return object_keys


def wait_for_job(
    client: Any,
    job_id: str,
    poll_seconds: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Wait for an AWS Data Exchange job to reach a terminal state."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        job = client.get_job(JobId=job_id)
        state = job["State"]
        LOGGER.info("Data Exchange import job %s state: %s", job_id, state)
        if state == "COMPLETED":
            return job
        if state in {"ERROR", "CANCELLED", "CANCELED"}:
            details = job.get("Errors", job.get("Details", ""))
            raise RuntimeError(f"Import job ended in {state}: {details}")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Import job {job_id} did not finish within "
                f"{timeout_seconds} seconds"
            )
        time.sleep(poll_seconds)


def publish_revision(
    client: Any,
    dataset_id: str,
    bucket: str,
    object_keys: list[str],
    poll_seconds: int,
    timeout_seconds: int,
) -> dict[str, str]:
    """Create, import, and finalize one Data Exchange revision."""
    revision = client.create_revision(DataSetId=dataset_id)
    revision_id = revision["Id"]
    LOGGER.info("Created Data Exchange revision %s", revision_id)

    job = client.create_job(
        Type="IMPORT_ASSETS_FROM_S3",
        Details={
            "ImportAssetsFromS3": {
                "DataSetId": dataset_id,
                "RevisionId": revision_id,
                "AssetSources": [
                    {"Bucket": bucket, "Key": object_key}
                    for object_key in object_keys
                ],
            }
        },
    )
    job_id = job["Id"]
    client.start_job(JobId=job_id)
    wait_for_job(client, job_id, poll_seconds, timeout_seconds)

    client.update_revision(
        DataSetId=dataset_id,
        RevisionId=revision_id,
        Comment=f"Imported {len(object_keys)} pipeline partition(s)",
        Finalized=True,
    )
    LOGGER.info("Finalized Data Exchange revision %s", revision_id)
    return {
        "dataset_id": dataset_id,
        "revision_id": revision_id,
        "job_id": job_id,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run, upload, and publish the public data pipeline revision."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument(
        "--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS
    )
    parser.add_argument(
        "--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def run_workflow(args: argparse.Namespace) -> int:
    """Run the pipeline, upload its partitions, and publish the revision."""
    os.chdir(SCRIPT_DIR)
    config = PipelineConfig.from_json(args.config)
    manifest = asyncio.run(run_pipeline(config))
    if manifest.get("failed_sources", 0):
        raise RuntimeError(
            f"Pipeline completed with "
            f"{manifest['failed_sources']} failed source(s)"
        )
    revision = manifest["revision"]
    revision_dir = config.output_dir / f"revision={revision}"

    s3_client = boto3.client("s3", region_name=args.region)
    object_keys = upload_revision(
        s3_client,
        args.bucket,
        args.prefix,
        revision,
        revision_dir,
        manifest,
    )
    exchange_client = boto3.client("dataexchange", region_name=args.region)
    result = publish_revision(
        exchange_client,
        args.dataset_id,
        args.bucket,
        object_keys,
        args.poll_seconds,
        args.timeout_seconds,
    )
    print(
        json.dumps(
            {"revision": revision, "s3_objects": object_keys, **result},
            indent=2,
        )
    )
    return 0


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    if args.poll_seconds < 1 or args.timeout_seconds < 1:
        print("Polling and timeout values must be positive.", file=sys.stderr)
        return 2

    try:
        return run_workflow(args)
    except NoCredentialsError:
        print("AWS credentials were not found.", file=sys.stderr)
        return 2
    except ClientError as error:
        code, message = describe_error(error)
        print(f"AWS request failed ({code}): {message}", file=sys.stderr)
        return 1
    except (
        BotoCoreError,
        KeyError,
        OSError,
        RuntimeError,
        TimeoutError,
        ValueError,
    ) as error:
        LOGGER.exception("Pipeline publication failed")
        print(f"Pipeline publication failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
