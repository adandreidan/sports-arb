import re
import time
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import config

GAME_LABEL = "PHI 76ers @ NY Knicks"


class DraftKingsScraper:

    def __init__(self):
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1400,900")
        self.driver = uc.Chrome(options=options, headless=False, version_main=147)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)

    def get_player_props(self) -> list:
        print(f"[DraftKings] Loading: {config.DK_GAME_URL}")
        self.driver.get(config.DK_GAME_URL)
        print("[DraftKings] Waiting 8s...")
        time.sleep(8)

        # Click POINTS tab
        try:
            tab = self.driver.find_element(
                By.XPATH,
                '//*[normalize-space(.)="POINTS" and not(*)]'
            )
            self.driver.execute_script("arguments[0].click();", tab)
            print("[DraftKings] Clicked POINTS tab")
        except Exception:
            print("[DraftKings] POINTS tab not found")
        time.sleep(3)

        for el in self.driver.find_elements(By.XPATH,
                '//*[@aria-expanded="false"][@aria-label]'):
            if "To Score" in (el.get_attribute("aria-label") or ""):
                self.driver.execute_script("arguments[0].click();", el)
                time.sleep(0.5)
        time.sleep(3)

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
                "player":     player,
                "line":       str(float(threshold) - 0.5),
                "over_odds":  odds,
                "under_odds": "N/A",
                "book":       "draftkings",
                "game":       GAME_LABEL,
                "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        print(f"[DraftKings] Found {len(props)} props")
        return props

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass
