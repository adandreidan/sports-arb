import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config


class FanDuelScraper:

    def __init__(self):
        options = Options()
        options.debugger_address = f"localhost:{config.REMOTE_DEBUG_PORT}"
        self.driver = webdriver.Chrome(options=options)
        print("[FanDuel] Connected to existing Chrome")

    def get_player_props(self) -> list:
        elements = self.driver.find_elements(By.XPATH, '//*[@aria-label]')
        over_map = {}   # (player_lower, threshold) -> (player, odds)
        under_map = {}  # (player_lower, threshold) -> (player, odds)

        for el in elements:
            label = el.get_attribute("aria-label") or ""
            if "Points" not in label:
                continue
            parts = [p.strip() for p in label.split(",")]
            if len(parts) != 3:
                continue
            thresh_match = re.search(r"(\d+)\+", parts[0])
            if not thresh_match:
                continue
            threshold = int(thresh_match.group(1))
            player = parts[1]
            odds = parts[2].replace("−", "-")
            if not player or not re.match(r"^[+\-]\d{2,5}$", odds):
                continue
            key = (player.lower(), threshold)
            is_under = re.search(r"\bNot\b", parts[0], re.IGNORECASE)
            if is_under:
                under_map[key] = (player, odds)
            else:
                over_map[key] = (player, odds)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        props = []
        for key in set(over_map) | set(under_map):
            player = (over_map.get(key) or under_map.get(key))[0]
            threshold = key[1]
            props.append({
                "player": player,
                "line": str(float(threshold) - 0.5),
                "over_odds": over_map[key][1] if key in over_map else "N/A",
                "under_odds": under_map[key][1] if key in under_map else "N/A",
                "book": "fanduel",
                "timestamp": timestamp,
            })

        print(f"[FanDuel] Found {len(props)} props")
        return props

    def close(self):
        pass
