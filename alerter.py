import json
from datetime import datetime

import requests

import config


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
    if not config.DISCORD_WEBHOOK:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    embed = {
        "title": "ARB FOUND",
        "color": 0x00FF00,
        "fields": [
            {"name": "Player / Prop / Line", "value": f"{player} — {prop} {line}", "inline": False},
            {"name": book1.upper(), "value": f"Stake: ${stake1:.2f}  @  {odds1}", "inline": True},
            {"name": book2.upper(), "value": f"Stake: ${stake2:.2f}  @  {odds2}", "inline": True},
            {"name": "Profit %", "value": f"{profit_pct * 100:.2f}%", "inline": True},
            {"name": "Guaranteed Profit", "value": f"${guaranteed_profit:.2f}", "inline": True},
            {"name": "Timestamp", "value": timestamp, "inline": False},
        ],
    }

    try:
        response = requests.post(
            config.DISCORD_WEBHOOK,
            data=json.dumps({"embeds": [embed]}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 204:
            print(f"[alerter] Discord embed sent for {player}")
        else:
            print(f"[alerter] Discord webhook returned {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[alerter] ERROR: {e}")


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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  ARB FOUND — {timestamp}")
    print(f"  Player : {player}")
    print(f"  Prop   : {prop.upper()} — Line {line}")
    print(f"  Bet 1  : {book1.upper()} @ {odds1}  Stake ${stake1:.2f}")
    print(f"  Bet 2  : {book2.upper()} @ {odds2}  Stake ${stake2:.2f}")
    print(f"  Profit : {profit_pct * 100:.2f}%  →  ${guaranteed_profit:.2f} guaranteed")
    print(f"{'='*60}\n")


def _send_raw(content: str) -> None:
    if not config.DISCORD_WEBHOOK:
        return
    try:
        response = requests.post(
            config.DISCORD_WEBHOOK,
            data=json.dumps({"content": content}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 204:
            print(f"[alerter] Sent: {content!r}")
        else:
            print(f"[alerter] Discord returned {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[alerter] ERROR: {e}")


if __name__ == "__main__":
    _send_raw("Arb Scanner Online")
