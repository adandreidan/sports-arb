import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config


class DraftKingsScraper:

    def __init__(self):
        options = Options()
        options.debugger_address = f"localhost:{config.REMOTE_DEBUG_PORT}"
        self.driver = webdriver.Chrome(options=options)
        print("[DraftKings] Connected to existing Chrome")

    def get_player_props(self) -> list:
        elements = self.driver.find_elements(By.XPATH, '//*[@aria-label]')
        props = []
        seen = set()

        for el in elements:
            label = el.get_attribute("aria-label") or ""
            if "To Score" not in label or "Points" not in label:
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
            if key in seen:
                continue
            seen.add(key)
            props.append({
                "player": player,
                "line": str(float(threshold) - 0.5),
                "over_odds": odds,
                "under_odds": "N/A",
                "book": "draftkings",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        print(f"[DraftKings] Found {len(props)} props")
        return props

    def close(self):
        pass
