"""Modular async public-data crawler and partitioned formatter.

Configure only public endpoints that permit automated access. The crawlers do
not bypass authentication, CAPTCHAs, robots directives, or access controls.
Raw payloads from every crawler enter one asyncio.Queue before normalization,
deduplication, compression, and partitioned export.
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
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

LOGGER = logging.getLogger("multi_crawler_pipeline")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class RawPayload:
    crawler: str
    data_type: str
    source_url: str
    fetched_at: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class CrawlerConfig:
    name: str
    data_type: str
    url: str
    record_selector: str
    fields: dict[str, str]
    headers: dict[str, str]
    params: dict[str, str]
    enabled: bool = True


class BaseCrawler:
    """Shared robots, rate-limit, randomized-header, and retry behavior."""

    retry_statuses = frozenset({408, 425, 429, 500, 502, 503, 504})

    def __init__(
        self,
        config: CrawlerConfig,
        user_agents: Iterable[str],
        requests_per_second: float = 1.0,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.config = config
        self.user_agents = tuple(user_agents)
        if not self.user_agents:
            raise ValueError("at least one user-agent is required")
        if requests_per_second <= 0 or max_retries < 0:
            raise ValueError("invalid rate-limit or retry setting")
        self.interval = 1.0 / requests_per_second
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._rate_lock = asyncio.Lock()
        self._next_request = 0.0
        self._robots: urllib.robotparser.RobotFileParser | None = None

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_lock:
            now = asyncio.get_running_loop().time()
            delay = max(0.0, self._next_request - now)
            self._next_request = max(now, self._next_request) + self.interval
        if delay:
            await asyncio.sleep(delay + random.uniform(0, self.interval * 0.2))

    async def _allowed_by_robots(self, session: aiohttp.ClientSession) -> bool:
        parsed = urlparse(self.config.url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = urllib.robotparser.RobotFileParser(robots_url)
        try:
            await self._wait_for_rate_limit()
            async with session.get(
                robots_url,
                headers={"User-Agent": random.choice(self.user_agents)},
            ) as response:
                if response.status == 404:
                    parser.parse([])
                elif response.status >= 400:
                    LOGGER.warning(
                        "Cannot read robots.txt for %s", self.config.name
                    )
                    return False
                else:
                    text = await response.text(errors="replace")
                    parser.parse(text.splitlines())
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            LOGGER.warning(
                "Robots check failed for %s: %s", self.config.name, error
            )
            return False
        self._robots = parser
        allowed = parser.can_fetch(self.user_agents[0], self.config.url)
        if not allowed:
            LOGGER.warning("robots.txt disallows %s", self.config.url)
        return allowed

    async def fetch_text(self, session: aiohttp.ClientSession) -> str:
        if not await self._allowed_by_robots(session):
            raise PermissionError(
                f"robots.txt disallows crawler: {self.config.name}"
            )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self._wait_for_rate_limit()
            headers = dict(self.config.headers)
            headers.setdefault("User-Agent", random.choice(self.user_agents))
            try:
                async with session.get(
                    self.config.url, headers=headers, params=self.config.params
                ) as response:
                    if response.status in self.retry_statuses:
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message="retryable HTTP status",
                        )
                    response.raise_for_status()
                    return await response.text(errors="replace")
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
                delay = min(60.0, 2**attempt + random.uniform(0, 0.5))
                LOGGER.warning(
                    "%s request failed (%d/%d): %s; retrying in %.1fs",
                    self.config.name,
                    attempt + 1,
                    self.max_retries + 1,
                    error,
                    delay,
                )
                await asyncio.sleep(delay)
        raise RuntimeError(
            f"request failed after retries: {self.config.name}"
        ) from last_error

    async def crawl(self, session: aiohttp.ClientSession) -> list[RawPayload]:
        raise NotImplementedError


class MunicipalZoningCrawler(BaseCrawler):
    """Extract permit/zoning rows using configured CSS selectors."""

    async def crawl(self, session: aiohttp.ClientSession) -> list[RawPayload]:
        document = await self.fetch_text(session)
        soup = BeautifulSoup(document, "html.parser")
        fetched_at = utc_now()
        payloads = []
        for element in soup.select(self.config.record_selector):
            values = {
                name: clean_text(
                    element.select_one(selector).get_text(" ", strip=True)
                    if element.select_one(selector)
                    else ""
                )
                for name, selector in self.config.fields.items()
            }
            values["source_url"] = self.config.url
            payloads.append(RawPayload(
                self.config.name,
                self.config.data_type,
                self.config.url,
                fetched_at,
                values,
            ))
        return payloads


class LogisticsTransitCrawler(BaseCrawler):
    """Extract logistics/transit rows with the shared crawler contract."""

    async def crawl(self, session: aiohttp.ClientSession) -> list[RawPayload]:
        document = await self.fetch_text(session)
        soup = BeautifulSoup(document, "html.parser")
        fetched_at = utc_now()
        payloads = []
        for element in soup.select(self.config.record_selector):
            values = {
                name: clean_text(
                    element.select_one(selector).get_text(" ", strip=True)
                    if element.select_one(selector)
                    else ""
                )
                for name, selector in self.config.fields.items()
            }
            values["source_url"] = self.config.url
            payloads.append(RawPayload(
                self.config.name,
                self.config.data_type,
                self.config.url,
                fetched_at,
                values,
            ))
        return payloads


class UnifiedProcessor:
    """Consume raw payloads, normalize records, deduplicate, and export."""

    def __init__(
        self, output_dir: str | Path, revision: str | None = None
    ) -> None:
        self.output_dir = Path(output_dir)
        self.revision = revision or datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        self.records: dict[str, dict[str, Any]] = {}

    async def consume(self, queue: asyncio.Queue[RawPayload | None]) -> None:
        while True:
            raw = await queue.get()
            try:
                if raw is None:
                    return
                record = self.normalize(raw)
                self.records.setdefault(record["fingerprint"], record)
            finally:
                queue.task_done()

    @staticmethod
    def normalize(raw: RawPayload) -> dict[str, Any]:
        record = {
            "data_type": clean_text(raw.data_type),
            "crawler": clean_text(raw.crawler),
            "source_url": clean_text(raw.source_url),
            "fetched_at": normalize_timestamp(raw.fetched_at),
            **{key: clean_text(value) for key, value in raw.payload.items()},
        }
        record["fingerprint"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return record

    def export(self) -> dict[str, Any]:
        revision_dir = self.output_dir / f"revision={self.revision}"
        revision_dir.mkdir(parents=True, exist_ok=False)
        partitions: dict[str, list[dict[str, Any]]] = {}
        for record in self.records.values():
            date = record["fetched_at"][:10]
            partitions.setdefault(
                f"data_type={record['data_type']}/observed_date={date}", []
            ).append(record)
        files = []
        for partition, records in sorted(partitions.items()):
            directory = revision_dir / partition
            directory.mkdir(parents=True, exist_ok=True)
            ndjson_path = directory / "records.ndjson.gz"
            with gzip.open(ndjson_path, "wt", encoding="utf-8") as stream:
                for record in records:
                    stream.write(json.dumps(record, sort_keys=True) + "\n")
            parquet_path = directory / "records.parquet"
            parquet_written = False
            try:
                pd.DataFrame(records).to_parquet(
                    parquet_path, index=False, compression="snappy"
                )
                parquet_written = True
            except (ImportError, ValueError) as error:
                LOGGER.warning("Parquet unavailable; kept NDJSON: %s", error)
            files.append({
                "partition": partition,
                "records": len(records),
                "ndjson_gzip": str(
                    ndjson_path.relative_to(revision_dir)
                ).replace("\\", "/"),
                "ndjson_sha256": sha256_file(ndjson_path),
                "parquet": (
                    str(parquet_path.relative_to(revision_dir)).replace("\\", "/")
                    if parquet_written
                    else None
                ),
            })
        manifest = {
            "schema": "public-multi-crawler.v1",
            "revision": self.revision,
            "created_at": utc_now(),
            "record_count": len(self.records),
            "partitions": files,
            "compression": "gzip NDJSON; optional Snappy Parquet",
        }
        (revision_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return manifest


def clean_text(value: Any) -> str:
    return WHITESPACE.sub(" ", CONTROL_CHARS.sub("", str(value or ""))).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: Any) -> str:
    parsed = pd.to_datetime(clean_text(value), utc=True, errors="coerce")
    if pd.isna(parsed):
        return utc_now()
    return parsed.isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_crawler(config: CrawlerConfig, **settings: Any) -> BaseCrawler:
    crawler_type = (
        MunicipalZoningCrawler
        if config.data_type == "municipal_permits"
        else LogisticsTransitCrawler
    )
    return crawler_type(config, **settings)


async def run_pipeline(config_path: Path, output_dir: Path) -> dict[str, Any]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    user_agents = raw.get("user_agents", ["GravitonMultiCrawler/1.0"])
    crawlers = [
        make_crawler(
            CrawlerConfig(
                name=item["name"],
                data_type=item["data_type"],
                url=item["url"],
                record_selector=item["record_selector"],
                fields=item["fields"],
                headers=item.get("headers", {}),
                params=item.get("params", {}),
                enabled=item.get("enabled", True),
            ),
            user_agents=user_agents,
            requests_per_second=float(raw.get("requests_per_second", 1.0)),
            max_retries=int(raw.get("max_retries", 3)),
            timeout_seconds=float(raw.get("timeout_seconds", 30)),
        )
        for item in raw.get("crawlers", [])
        if item.get("enabled", True)
    ]
    queue_size = int(raw.get("queue_size", 1000))
    queue: asyncio.Queue[RawPayload | None] = asyncio.Queue(maxsize=queue_size)
    processor = UnifiedProcessor(output_dir)
    consumer = asyncio.create_task(processor.consume(queue))
    connector = aiohttp.TCPConnector(limit=int(raw.get("max_concurrency", 4)))
    async with aiohttp.ClientSession(connector=connector) as session:
        results = await asyncio.gather(
            *(crawler.crawl(session) for crawler in crawlers),
            return_exceptions=True,
        )
    failures = []
    for crawler, result in zip(crawlers, results):
        if isinstance(result, Exception):
            failures.append(f"{crawler.config.name}: {result}")
            continue
        for payload in result:
            await queue.put(payload)
    await queue.put(None)
    await queue.join()
    await consumer
    manifest = processor.export()
    manifest["failures"] = failures
    revision_dir = output_dir / f"revision={processor.revision}"
    (revision_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("multi_crawler_revisions")
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        manifest = asyncio.run(run_pipeline(args.config, args.output))
        print(json.dumps(manifest, indent=2))
        return 2 if manifest["failures"] else 0
    except (OSError, ValueError, RuntimeError, aiohttp.ClientError) as error:
        LOGGER.exception("Pipeline failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
