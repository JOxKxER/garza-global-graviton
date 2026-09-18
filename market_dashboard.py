"""Terminal dashboard for the Glacier-to-Ripple market pipeline."""

import os
import sqlite3
import time
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "data_in" / "mesh_telemetry.db"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def fetch_dashboard_data() -> dict[str, object]:
    if not DB_PATH.exists():
        return {
            "tickers": [], "macro": None, "rebound": [],
            "subgroups": [], "micro": [],
        }

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        tickers = connection.execute(
            """
            SELECT symbol, price, change_percent, volume, recorded_at
            FROM market_ticker_telemetry
            WHERE rowid IN (
                SELECT MAX(rowid) FROM market_ticker_telemetry GROUP BY symbol
            )
            ORDER BY symbol
            """
        ).fetchall()
        macro = _latest(connection, "macro_market_telemetry")
        rebound = _recent(connection, "structural_rebound_watch", 8)
        subgroups = _recent(connection, "subgroup_signal_analysis", 5)
        micro = _recent(connection, "micro_transaction_actionables", 8)
    return {
        "tickers": tickers,
        "macro": macro,
        "rebound": rebound,
        "subgroups": subgroups,
        "micro": micro,
    }


def _latest(connection: sqlite3.Connection, table: str):
    if not _table_exists(connection, table):
        return None
    return connection.execute(
        f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1"
    ).fetchone()


def _recent(connection: sqlite3.Connection, table: str, limit: int):
    if not _table_exists(connection, table):
        return []
    return connection.execute(
        f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?", (limit,)
    ).fetchall()


def main() -> None:
    try:
        while True:
            clear_screen()
            data = fetch_dashboard_data()
            print("=" * 78)
            print(" JOKER MESH MARKET | GLACIER -> FRACTURE -> RIPPLE")
            print("=" * 78)
            print(f" Local Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            macro = data["macro"]
            print("--- MACRO GLACIER OUTLOOK ---")
            print(
                macro["outlook"]
                if macro
                else "Waiting for macro baseline..."
            )
            print("\n--- BENCHMARK SNAPSHOT ---")
            if macro:
                print(macro["benchmarks_json"])
            else:
                print("Waiting for SPY / QQQ / VIX / sector telemetry...")

            print("\n--- STRUCTURAL REBOUND & RIPPLE WATCH ---")
            if data["rebound"]:
                for watch in data["rebound"]:
                    print(
                        f"  {watch['symbol']:<6} "
                        f"P={watch['recovery_probability']!s:<6} "
                        f"{watch['catalyst_type']}: "
                        f"{watch['timing_window']}"
                    )
                    print(
                        f"    Distress: {watch['distress_evidence']} | "
                        f"Invalidation: {watch['invalidation']}"
                    )
            else:
                print(
                    "  No structural rebound candidates; continue monitoring."
                )

            print("\n--- FRACTURE ZONE PROBABILITIES ---")
            if data["subgroups"]:
                for group in data["subgroups"]:
                    print(
                        f"  {group['subgroup']:<24} "
                        f"{group['direction']:<8} "
                        f"P={group['probability']!s:<6} "
                        f"{group['rationale']}"
                    )
            else:
                print("  Waiting for subgroup probability analysis...")

            print("\n--- MICRO-TRANSACTION ACTIONABLES ---")
            if data["micro"]:
                for action in data["micro"]:
                    print(
                        f"  {action['symbol']:<6} {action['action']:<10} "
                        f"shares={action['shares']!s:<8} "
                        f"risk=${action['dollar_risk']!s:<6} "
                        f"{action['rationale']}"
                    )
            else:
                print("  No micro actionables; default posture is NO TRADE.")

            print("\n--- LIVE TICKERS ---")
            for ticker in data["tickers"]:
                change = ticker["change_percent"]
                change_text = "n/a" if change is None else f"{change:>6.2f}%"
                volume = ticker["volume"] or 0
                print(
                    f"  {ticker['symbol']:<6} ${ticker['price']:<9.2f} "
                    f"change={change_text} volume={volume:,}"
                )
            print("\nRefresh: 15 seconds. Press Ctrl+C to exit.")
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nDashboard closed.")


if __name__ == "__main__":
    main()
