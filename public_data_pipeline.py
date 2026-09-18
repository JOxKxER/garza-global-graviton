"""Headless public-domain web ingestion and cloud-ready dataset packager.

The pipeline fetches configured public pages, extracts records using CSS selectors,
normalizes and validates them, removes duplicate records by SHA-256 fingerprint,
and writes revisioned gzip-compressed NDJSON partitions plus a manifest. The
resulting directory can be uploaded to S3 or another S3-compatible object store.

Example:
    python public_data_pipeline.py --config pipeline.json

The module intentionally does not upload data itself. Keeping upload separate
makes local output inspectable and lets an AWS Data Exchange or S3 job apply its
own credentials and transfer policy.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import logging
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

LOGGER = logging.getLogger("public_data_pipeline")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class FieldSpec:
    """CSS extraction rule for one output field."""

    name: str
    selector: str
    attribute: str = "text"
    required: bool = False


@dataclass(frozen=True)
class SourceSpec:
    """A public page and the selectors used to extract its records."""

    name: str
    url: str
    record_selector: str
    fields: tuple[FieldSpec, ...]
    format: str = "html"
    records_path: str = ""


@dataclass
class PipelineConfig:
    """Operational settings loaded from JSON or constructed in Python."""

    output_dir: Path = Path("dataset_revisions")
    revision: str = ""
    max_concurrency: int = 8
    requests_per_second: float = 1.0
    timeout_seconds: float = 30.0
    max_retries: int = 4
    backoff_base_seconds: float = 1.0
    user_agents: list[str] = field(default_factory=lambda: [
        "PublicDataPipeline/1.0 (+https://example.org/contact)",
        "Mozilla/5.0 (compatible; PublicDataPipeline/1.0)",
    ])
    sources: list[SourceSpec] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> "PipelineConfig":
        with Path(path).open("r", encoding="utf-8") as stream:
            raw = json.load(stream)
        sources = []
        for source in raw.pop("sources", []):
            field_specs = tuple(
                FieldSpec(**field_data) for field_data in source.pop("fields")
            )
            sources.append(SourceSpec(fields=field_specs, **source))
        raw["output_dir"] = Path(raw.get("output_dir", "dataset_revisions"))
        return cls(sources=sources, **raw)

    def validate(self) -> None:
        if not self.sources:
            raise ValueError("at least one source is required")
        if self.max_concurrency < 1 or self.max_retries < 0:
            raise ValueError("max_concurrency must be positive and max_retries non-negative")
        if self.requests_per_second <= 0 or self.timeout_seconds <= 0:
            raise ValueError("requests_per_second and timeout_seconds must be positive")
        if not self.user_agents:
            raise ValueError("at least one user-agent is required")
        for source in self.sources:
            parsed = urlparse(source.url)
            if parsed.scheme not in {"http", "https"}:
                raise ValueError(f"unsupported source URL: {source.url}")
            if not source.fields:
                raise ValueError(f"source has no fields: {source.name}")


class PoliteRateLimiter:
    """Simple global request limiter with jitter to avoid bursty traffic."""

    def __init__(self, requests_per_second: float) -> None:
        self._interval = 1.0 / requests_per_second
        self._lock = asyncio.Lock()
        self._next_request = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_running_loop().time()
            delay = max(0.0, self._next_request - now)
            self._next_request = max(now, self._next_request) + self._interval
        if delay:
            await asyncio.sleep(delay + random.uniform(0, self._interval * 0.2))


class AsyncFetcher:
    """Fetch pages concurrently while applying retries, backoff, and headers."""

    RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.limiter = PoliteRateLimiter(config.requests_per_second)
        self.semaphore = asyncio.Semaphore(config.max_concurrency)

    async def fetch(self, client: httpx.AsyncClient, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            await self.limiter.wait()
            headers = {
                "User-Agent": random.choice(self.config.user_agents),
                "Accept": "text/html,application/xhtml+xml",
            }
            try:
                async with self.semaphore:
                    response = await client.get(url, headers=headers)
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    raise httpx.HTTPStatusError(
                        f"retryable HTTP status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                retry_delay = self.config.backoff_base_seconds * (2**attempt)
                retry_delay += random.uniform(0, retry_delay * 0.25)
                retry_after = self._retry_after(
                    exc.response.headers.get("Retry-After")
                )
                retry_delay = max(retry_delay, retry_after)
                LOGGER.warning(
                    "Request failed for %s (attempt %d/%d): %s; retrying in %.2fs",
                    url, attempt + 1, self.config.max_retries + 1, exc, retry_delay,
                )
                await asyncio.sleep(retry_delay)
            except (httpx.HTTPError, OSError) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                retry_delay = self.config.backoff_base_seconds * (2**attempt)
                retry_delay += random.uniform(0, retry_delay * 0.25)
                LOGGER.warning(
                    "Request failed for %s (attempt %d/%d): %s; "
                    "retrying in %.2fs",
                    url,
                    attempt + 1,
                    self.config.max_retries + 1,
                    exc,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
        raise RuntimeError(f"request failed after retries: {url}") from last_error

    @staticmethod
    def _retry_after(value: str | None) -> float:
        if not value:
            return 0.0
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return 0.0


class RecordSanitizer:
    """Normalize fields and enforce the output record contract."""

    REQUIRED_FIELDS = {"source", "source_url", "title", "observed_at", "fingerprint"}

    @staticmethod
    def text(value: Any) -> str:
        value = "" if value is None else str(value)
        value = CONTROL_CHARS.sub("", value)
        return WHITESPACE.sub(" ", value).strip()

    @classmethod
    def timestamp(cls, value: Any) -> str:
        raw = cls.text(value)
        if not raw:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @classmethod
    def normalize(cls, raw: dict[str, Any]) -> dict[str, str]:
        normalized = {key: cls.text(value) for key, value in raw.items()}
        normalized["source"] = cls.text(normalized.get("source"))
        normalized["source_url"] = cls.text(normalized.get("source_url"))
        normalized["title"] = cls.text(normalized.get("title"))
        normalized["observed_at"] = cls.timestamp(normalized.get("observed_at"))
        fingerprint_input = {
            key: normalized.get(key, "")
            for key in sorted(normalized)
            if key != "fingerprint"
        }
        normalized["fingerprint"] = hashlib.sha256(
            json.dumps(fingerprint_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return normalized

    @classmethod
    def validate(cls, record: dict[str, str]) -> None:
        missing = cls.REQUIRED_FIELDS - record.keys()
        if missing:
            raise ValueError(f"missing required fields: {sorted(missing)}")
        for field_name in cls.REQUIRED_FIELDS:
            if not record[field_name]:
                raise ValueError(f"required field is empty: {field_name}")
        if not re.fullmatch(r"[0-9a-f]{64}", record["fingerprint"]):
            raise ValueError("fingerprint is not a SHA-256 hex digest")
        datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))


def extract_records(source: SourceSpec, document: str) -> list[dict[str, Any]]:
    if source.format == "json":
        payload = json.loads(document)
        records: Any = payload
        for path_part in filter(None, source.records_path.split(".")):
            if not isinstance(records, dict):
                raise ValueError(f"JSON path is not an object: {source.records_path}")
            records = records.get(path_part, [])
        if not isinstance(records, list):
            raise ValueError(f"JSON records path is not a list: {source.records_path}")
        extracted: list[dict[str, Any]] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            raw = {"source": source.name, "source_url": source.url}
            for field_spec in source.fields:
                value: Any = item
                for path_part in filter(None, field_spec.selector.split(".")):
                    value = value.get(path_part, "") if isinstance(value, dict) else ""
                raw[field_spec.name] = value
            extracted.append(raw)
        return extracted

    if source.format != "html":
        raise ValueError(f"unsupported source format: {source.format}")

    soup = BeautifulSoup(document, "html.parser")
    records: list[dict[str, Any]] = []
    for element in soup.select(source.record_selector):
        raw: dict[str, Any] = {"source": source.name, "source_url": source.url}
        for field_spec in source.fields:
            selected = element.select_one(field_spec.selector)
            if selected is None:
                if field_spec.required:
                    raise ValueError(
                        f"required selector not found: {field_spec.name}"
                    )
                raw[field_spec.name] = ""
                continue
            if field_spec.attribute == "text":
                raw[field_spec.name] = selected.get_text(" ", strip=True)
            else:
                raw[field_spec.name] = urljoin(
                    source.url, selected.get(field_spec.attribute, "")
                )
        records.append(raw)
    return records


def write_partitioned_revision(
    records: Iterable[dict[str, str]], config: PipelineConfig
) -> tuple[Path, dict[str, Any]]:
    revision = config.revision or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    revision_dir = config.output_dir / f"revision={revision}"
    revision_dir.mkdir(parents=True, exist_ok=False)
    partitions: dict[str, list[dict[str, str]]] = {}
    for record in records:
        partition_key = record["observed_at"][:10]
        partitions.setdefault(partition_key, []).append(record)

    files: list[dict[str, Any]] = []
    for partition_key, partition_records in sorted(partitions.items()):
        relative_path = Path(f"observed_date={partition_key}") / "data.ndjson.gz"
        output_path = revision_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(output_path, "wt", encoding="utf-8", newline="\n") as stream:
            for record in partition_records:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        files.append({
            "path": str(relative_path).replace("\\", "/"),
            "records": len(partition_records),
            "sha256": sha256_file(output_path),
            "bytes": output_path.stat().st_size,
        })

    manifest = {
        "manifest_version": "1.0",
        "dataset_schema": "public-domain-target.v1",
        "revision": revision,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "format": "gzip-compressed NDJSON",
        "compression": "gzip",
        "encoding": "UTF-8",
        "record_count": sum(item["records"] for item in files),
        "partitions": files,
        "integrity": "SHA-256 of each compressed partition",
        "upload_target": "S3-compatible object storage",
    }
    manifest_path = revision_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return revision_dir, manifest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def run_pipeline(config: PipelineConfig) -> dict[str, Any]:
    config.validate()
    sanitizer = RecordSanitizer()
    fetcher = AsyncFetcher(config)
    unique_records: dict[str, dict[str, str]] = {}
    failed_sources = 0

    async with httpx.AsyncClient(timeout=config.timeout_seconds, follow_redirects=True) as client:
        async def process_source(source: SourceSpec) -> None:
            nonlocal failed_sources
            try:
                document = await fetcher.fetch(client, source.url)
                for raw_record in extract_records(source, document):
                    record = sanitizer.normalize(raw_record)
                    sanitizer.validate(record)
                    unique_records.setdefault(record["fingerprint"], record)
            except (OSError, ValueError, KeyError, TypeError, RuntimeError):
                failed_sources += 1
                LOGGER.exception("Source failed: %s", source.name)

        await asyncio.gather(*(process_source(source) for source in config.sources))

    revision_dir, manifest = write_partitioned_revision(
        unique_records.values(), config
    )
    manifest["failed_sources"] = failed_sources
    (revision_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    LOGGER.info("Wrote %d unique records to %s", manifest["record_count"], revision_dir)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Path to a JSON pipeline configuration")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    try:
        manifest = asyncio.run(run_pipeline(PipelineConfig.from_json(args.config)))
        LOGGER.info("Revision complete: %s", json.dumps(manifest, sort_keys=True))
        return 0 if manifest["failed_sources"] == 0 else 2
    except Exception:
        LOGGER.exception("Pipeline failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
