import re
import time
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import config

GAME_LABEL = "PHI 76ers @ NY Knicks"


class FanDuelScraper:

    def __init__(self):
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1400,900")
        self.driver = uc.Chrome(options=options, headless=False, version_main=147)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)

    def get_player_props(self) -> list:
        print(f"[FanDuel] Loading: {config.FD_GAME_URL}")
        self.driver.get(config.FD_GAME_URL)
        print("[FanDuel] Waiting 8s...")
        time.sleep(8)

        page_text = self.driver.find_element(By.TAG_NAME, "body").text[:200]
        print(f"[FanDuel] Page snippet: {page_text!r}")

        # If bot challenge, wait up to 60s for manual solve
        if "Press & Hold" in page_text or "confirm you are" in page_text.lower():
            print("[FanDuel] Bot challenge detected — waiting 60s for manual solve...")
            time.sleep(60)

        candidates = self.driver.find_elements(By.XPATH,
            '//*[@aria-expanded="false"][@aria-label]')
        print(f"[FanDuel] aria-expanded=false elements: {len(candidates)}")
        for el in candidates:
            label = el.get_attribute("aria-label") or ""
            if "To Score" in label:
                print(f"[FanDuel]   Clicking: {label}")
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
            # Expected: "To Score 5+ Points, Josh Hart, -2200"
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
                "book":       "fanduel",
                "game":       GAME_LABEL,
                "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        print(f"[FanDuel] Found {len(props)} props")
        return props

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass
