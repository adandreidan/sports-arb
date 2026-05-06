# logger.py — CSV logging for discovered arbitrage opportunities

import csv
import os
from datetime import datetime

import config


# Column headers for the CSV log file
CSV_HEADERS = [
    "time",
    "player",
    "prop",
    "line",
    "book1",
    "odds1",
    "stake1",
    "book2",
    "odds2",
    "stake2",
    "profit_pct",
    "guaranteed_profit",
]


def log_arb(
    player: str,
    prop: str,
    line: str,
    book1: str,
    odds1: str,
    stake1: float,
    book2: str,
    odds2: str,
    stake2: float,
    profit_pct: float,
    guaranteed_profit: float,
) -> None:
    """
    Append one arbitrage opportunity as a row in the CSV log file.

    Creates the file with headers if it does not already exist.
    Each call appends one row — the file grows over time.

    Args:
        player           — Player name (e.g. "LeBron James")
        prop             — Prop type (e.g. "points")
        line             — The line number (e.g. "23.5")
        book1            — Name of first sportsbook (e.g. "fanduel")
        odds1            — American odds on book1 (e.g. "-114")
        stake1           — Dollar amount to bet on book1
        book2            — Name of second sportsbook (e.g. "draftkings")
        odds2            — American odds on book2
        stake2           — Dollar amount to bet on book2
        profit_pct       — Profit as decimal (e.g. 0.039)
        guaranteed_profit — Guaranteed dollar profit
    """
    try:
        file_exists = os.path.isfile(config.LOG_FILE)

        with open(config.LOG_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)

            # Write headers only when creating the file for the first time
            if not file_exists:
                writer.writeheader()
                print(f"[logger] Created new log file: {config.LOG_FILE}")

            writer.writerow(
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "player": player,
                    "prop": prop,
                    "line": line,
                    "book1": book1,
                    "odds1": odds1,
                    "stake1": f"{stake1:.2f}",
                    "book2": book2,
                    "odds2": odds2,
                    "stake2": f"{stake2:.2f}",
                    "profit_pct": f"{profit_pct * 100:.2f}%",
                    "guaranteed_profit": f"{guaranteed_profit:.2f}",
                }
            )
        print(f"[logger] Logged arb: {player} {prop} {line} ({book1} vs {book2})")

    except Exception as e:
        print(f"[logger] ERROR writing to log file: {e}")


def log_summary() -> None:
    """
    Read the CSV log file and print a summary to terminal.

    Shows total number of arb opportunities found and total
    guaranteed profit identified across all logged entries.
    """
    try:
        if not os.path.isfile(config.LOG_FILE):
            print("[logger] No log file found — no arbs have been logged yet.")
            return

        total_arbs = 0
        total_profit = 0.0

        with open(config.LOG_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_arbs += 1
                try:
                    total_profit += float(row["guaranteed_profit"])
                except ValueError:
                    pass  # skip malformed rows

        print("\n" + "=" * 50)
        print("SESSION SUMMARY")
        print("=" * 50)
        print(f"  Total arbs found   : {total_arbs}")
        print(f"  Total profit found : ${total_profit:.2f}")
        print("=" * 50)

    except Exception as e:
        print(f"[logger] ERROR reading log file for summary: {e}")
