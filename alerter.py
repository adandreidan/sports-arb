# alerter.py — Alerting for discovered arbitrage opportunities

import json
from datetime import datetime

import requests

import config


def print_alert(
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
    Print a formatted arbitrage alert to the terminal with emojis.

    Shows the player, prop line, which book to bet each side on,
    exact dollar stakes, profit percentage, and guaranteed profit.

    Args:
        player           — Player name
        prop             — Prop type (e.g. "points")
        line             — The line number (e.g. "23.5")
        book1            — Name of first sportsbook
        odds1            — American odds on book1
        stake1           — Dollar amount to wager on book1
        book2            — Name of second sportsbook
        odds2            — American odds on book2
        stake2           — Dollar amount to wager on book2
        profit_pct       — Profit as decimal (e.g. 0.039)
        guaranteed_profit — Guaranteed dollar profit
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "🚨" * 30)
    print(f"   ARB FOUND — {timestamp}")
    print(f"   Player  : {player}")
    print(f"   Prop    : {prop.upper()} — Line {line}")
    print(f"   Bet 1   : {book1.upper()} @ {odds1}  ➜  Stake ${stake1:.2f}")
    print(f"   Bet 2   : {book2.upper()} @ {odds2}  ➜  Stake ${stake2:.2f}")
    print(f"   Profit  : {profit_pct * 100:.2f}%  →  ${guaranteed_profit:.2f} guaranteed")
    print("\n")


def send_discord_alert(
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
    Send an arbitrage alert to a Discord channel via webhook.

    Only executes if DISCORD_WEBHOOK is set in config.py.
    Silently skips if no webhook is configured.

    Args: same as print_alert()
    """
    # Skip if no webhook is configured
    if not config.DISCORD_WEBHOOK:
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"🚨 **ARB FOUND** — {timestamp}\n"
            f"🏀 **Player**: {player}\n"
            f"📊 **Prop**: {prop.upper()} — Line {line}\n"
            f"📗 **Bet 1**: {book1.upper()} @ {odds1}  →  Stake **${stake1:.2f}**\n"
            f"📘 **Bet 2**: {book2.upper()} @ {odds2}  →  Stake **${stake2:.2f}**\n"
            f"📈 **Profit**: {profit_pct * 100:.2f}%  →  **${guaranteed_profit:.2f} guaranteed**"
        )

        payload = {"content": message}

        response = requests.post(
            config.DISCORD_WEBHOOK,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 204:
            print(f"[alerter] Discord alert sent for {player}")
        else:
            print(f"[alerter] Discord webhook returned status {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"[alerter] ERROR sending Discord alert: {e}")
    except Exception as e:
        print(f"[alerter] Unexpected error in send_discord_alert: {e}")
