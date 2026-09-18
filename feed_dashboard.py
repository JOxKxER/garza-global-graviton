"""Continuously feed informational demo odds into the local dashboard database.

This feeder generates clearly labeled simulated data for UI development when a
live odds provider is not configured. It never places wagers or contacts a
sportsbook. Replace the generator with an approved public connector when live
informational data is needed.
"""

from __future__ import annotations

import argparse
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sports_analytics_engine import OddsRecord, SQLiteStore, utc_now


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "sports_analytics.db"
DEFAULT_INTERVAL = 15
LOGGER = logging.getLogger("feed_dashboard")


TEAMS = (
    ("demo-nba-001", "Boston Comets", "Phoenix Orbit"),
    ("demo-nba-002", "Chicago Foundry", "Seattle Cascades"),
    ("demo-nba-003", "Miami Current", "Denver Peaks"),
)
BOOKMAKERS = ("Demo Reference A", "Demo Reference B", "Demo Reference C")


def decimal_to_american(decimal_price: float) -> int:
    """Convert a combined decimal price into an American display price."""
    if decimal_price <= 1:
        raise ValueError("decimal price must be greater than one")
    if decimal_price >= 2:
        return round((decimal_price - 1) * 100)
    return round(-100 / (decimal_price - 1))


def generate_records(cycle: int) -> list[OddsRecord]:
    """Generate one fresh, non-wagering snapshot for the dashboard."""
    observed_at = utc_now()
    commence_time = (
        datetime.now(timezone.utc) + timedelta(hours=3)
    ).isoformat().replace("+00:00", "Z")
    records: list[OddsRecord] = []

    for event_index, (event_id, home, away) in enumerate(TEAMS):
        for bookmaker_index, bookmaker in enumerate(BOOKMAKERS):
            home_shift = (cycle + event_index + bookmaker_index) % 7 - 3
            away_shift = (cycle * 2 + event_index + bookmaker_index) % 7 - 3
            home_price = -110 + home_shift * 5
            away_price = 100 + away_shift * 5
            for market, outcomes in (
                ("h2h", ((home, home_price), (away, away_price))),
                ("spreads", ((home, home_price - 8), (away, away_price + 8))),
                ("totals", (("Over", -105 + cycle % 4 * 5), ("Under", -115))),
            ):
                for outcome, price in outcomes:
                    records.append(
                        OddsRecord(
                            event_id=event_id,
                            sport="basketball_nba",
                            league="Demo Basketball League",
                            home_team=home,
                            away_team=away,
                            commence_time=commence_time,
                            bookmaker=bookmaker,
                            market=market,
                            outcome=outcome,
                            price_american=price,
                            point=220.5 if market == "totals" else -3.5,
                            observed_at=observed_at,
                            source="local-demo-feeder",
                        )
                    )

    # Composite scenarios are stored as ordinary odds records so the existing
    # dashboard can sort and analyze them alongside individual markets.
    parlay_legs = [
        (TEAMS[index][1], -110 + ((cycle + index) % 5 - 2) * 5)
        for index in range(len(TEAMS))
    ]
    for leg_count in (2, 3):
        selected_legs = parlay_legs[:leg_count]
        decimal_price = 1.0
        for _, price in selected_legs:
            decimal_price *= 1 / (
                abs(price) / (abs(price) + 100)
                if price < 0
                else 100 / (price + 100)
            )
        leg_names = " + ".join(name for name, _ in selected_legs)
        records.append(
            OddsRecord(
                event_id=f"demo-parlay-{leg_count}",
                sport="basketball_nba",
                league="Demo Basketball League",
                home_team="Multi-event",
                away_team="Composite scenario",
                commence_time=commence_time,
                bookmaker="Demo Parlay Composite",
                market="parlay",
                outcome=f"{leg_count}-leg: {leg_names}",
                price_american=decimal_to_american(decimal_price),
                point=None,
                observed_at=observed_at,
                source="local-demo-feeder-parlay",
            )
        )
    return records


def feed_once(store: SQLiteStore, cycle: int) -> int:
    records = generate_records(cycle)
    inserted = store.save(records)
    LOGGER.info(
        "Feeder cycle %d: generated %d records, inserted %d new snapshots",
        cycle,
        len(records),
        inserted,
    )
    return inserted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Feed simulated informational odds into the local dashboard."
        )
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--once", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if args.interval < 1:
        print("--interval must be at least 1 second")
        return 2

    store = SQLiteStore(args.db)
    cycle = random.randrange(1000)
    while True:
        feed_once(store, cycle)
        if args.once:
            return 0
        cycle += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
