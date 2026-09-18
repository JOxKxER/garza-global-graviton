"""RSS-based freelance gig tracker with SQLite persistence and Discord alerts."""

from __future__ import annotations

import argparse
import html
import logging
import os
import re
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import feedparser
import httpx


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR / "gig_tracker.db"
DEFAULT_POLICY_DB_PATH = SCRIPT_DIR / "vault_storage.db"
DEFAULT_FEEDS = (
    "https://remoteok.com/remote-data-jobs.rss",
    "https://remoteok.com/remote-python-jobs.rss",
)
DEFAULT_KEYWORDS = (
    "freelance",
    "contract",
    "data scraping",
    "web scraping",
    "scraping",
    "data extraction",
    "data entry",
    "data analyst",
    "data engineer",
    "etl",
    "automation",
    "crawler",
    "selenium",
    "playwright",
    "beautifulsoup",
    "python",
    "api integration",
)

logging.basicConfig(
    level=os.environ.get("BOT_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("gig_tracker")


def parse_csv(value: str | None, default: Iterable[str]) -> list[str]:
    """Return non-empty comma-separated values, or the supplied defaults."""
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def clean_text(value: Any) -> str:
    """Convert an RSS field to compact, readable plain text."""
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def matching_keywords(title: str, summary: str, keywords: Iterable[str]) -> list[str]:
    searchable_text = f"{title} {summary}".casefold()
    return [keyword for keyword in keywords if keyword.casefold() in searchable_text]


def initialize_database(db_path: str | Path) -> None:
    """Create the local job ledger if it does not exist."""
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT NOT NULL,
                published TEXT NOT NULL,
                source TEXT NOT NULL,
                matched_keywords TEXT NOT NULL,
                notified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_webhook_url(policy_db_path: str | Path) -> str:
    """Read the webhook from the environment, then from the existing policy DB."""
    configured_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if configured_url:
        return configured_url

    if not Path(policy_db_path).exists():
        return ""
    try:
        with closing(sqlite3.connect(policy_db_path)) as connection:
            row = connection.execute(
                "SELECT value FROM policies WHERE key = 'discord_webhook_url'"
            ).fetchone()
        return str(row[0]).strip() if row and row[0] else ""
    except sqlite3.Error as exc:
        LOGGER.warning("Could not read Discord webhook policy: %s", exc)
        return ""


def save_matching_jobs(
    db_path: str | Path,
    source: str,
    entries: Iterable[Any],
    keywords: Iterable[str],
) -> list[dict[str, str]]:
    """Filter feed entries, insert unseen matches, and return new jobs."""
    keyword_list = list(keywords)
    new_jobs: list[dict[str, str]] = []
    now = datetime.now(timezone.utc).isoformat()

    with closing(sqlite3.connect(db_path)) as connection:
        for entry in entries:
            title = clean_text(entry.get("title", "Untitled gig"))
            summary = clean_text(entry.get("summary", entry.get("description", "")))
            link = str(entry.get("link", "")).strip()
            if not link:
                continue

            matches = matching_keywords(title, summary, keyword_list)
            if not matches:
                continue

            job_key = str(entry.get("id", "")).strip() or link
            published = clean_text(entry.get("published", entry.get("updated", "")))
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO jobs
                    (job_key, title, link, summary, published, source,
                     matched_keywords, notified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (job_key, title, link, summary, published, source, ", ".join(matches), now),
            )
            if cursor.rowcount == 1:
                new_jobs.append(
                    {
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "published": published,
                        "source": source,
                        "matched_keywords": ", ".join(matches),
                    }
                )
        connection.commit()
    return new_jobs


def send_discord_notification(
    webhook_url: str,
    job: dict[str, str],
    client: httpx.Client | None = None,
) -> bool:
    """Post one matching job to Discord and return whether it was accepted."""
    if not webhook_url:
        return False

    payload = {
        "username": "Freelance Gig Tracker",
        "embeds": [
            {
                "title": job["title"][:256],
                "url": job["link"],
                "description": job["summary"][:4000] or "No description provided.",
                "color": 3447003,
                "fields": [
                    {"name": "Source", "value": job["source"][:1024], "inline": True},
                    {
                        "name": "Matched keywords",
                        "value": job["matched_keywords"][:1024],
                        "inline": True,
                    },
                ],
            }
        ],
    }

    try:
        if client is None:
            with httpx.Client(timeout=15.0) as owned_client:
                response = owned_client.post(webhook_url, json=payload)
        else:
            response = client.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        LOGGER.warning("Discord notification failed for %s: %s", job["link"], exc)
        return False


def mark_notified(db_path: str | Path, link: str) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("UPDATE jobs SET notified = 1 WHERE link = ?", (link,))
        connection.commit()


def poll_feeds(
    db_path: str | Path,
    feed_urls: Iterable[str],
    keywords: Iterable[str],
    webhook_url: str = "",
) -> int:
    """Fetch all feeds once, persist new matches, and notify Discord when configured."""
    total_new = 0
    for feed_url in feed_urls:
        try:
            parsed_feed = feedparser.parse(feed_url)
            if getattr(parsed_feed, "bozo", False) and not parsed_feed.entries:
                LOGGER.warning("RSS feed could not be parsed: %s", feed_url)
                continue
            jobs = save_matching_jobs(db_path, feed_url, parsed_feed.entries, keywords)
        except Exception as exc:  # Keep one broken feed from stopping the daemon.
            LOGGER.warning("RSS feed failed (%s): %s", feed_url, exc)
            continue

        for job in jobs:
            total_new += 1
            LOGGER.info("New matching gig: %s", job["title"])
            if webhook_url and send_discord_notification(webhook_url, job):
                mark_notified(db_path, job["link"])
    return total_new


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("BOT_INTERVAL_SECONDS", "300")))
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("BOT_DB_PATH", DEFAULT_DB_PATH)))
    parser.add_argument("--policy-db", type=Path, default=Path(os.environ.get("BOT_POLICY_DB_PATH", DEFAULT_POLICY_DB_PATH)))
    parser.add_argument("--feed", action="append", dest="feeds", help="RSS URL; may be supplied more than once.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.interval < 1:
        raise SystemExit("--interval must be at least 1 second")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(args.db)
    feeds = args.feeds or parse_csv(os.environ.get("RSS_FEEDS"), DEFAULT_FEEDS)
    keywords = parse_csv(os.environ.get("GIG_KEYWORDS"), DEFAULT_KEYWORDS)
    webhook_url = get_webhook_url(args.policy_db)

    LOGGER.info("Gig tracker started with %d feed(s); database: %s", len(feeds), args.db)
    while True:
        new_count = poll_feeds(args.db, feeds, keywords, webhook_url)
        LOGGER.info("Poll complete: %d new matching gig(s)", new_count)
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
