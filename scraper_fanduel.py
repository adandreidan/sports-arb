# scraper_fanduel.py

import re
import time
from datetime import datetime

import undetected_chromedriver as uc
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import config

GAME_LABEL = "PHI 76ers @ NY Knicks"

# Words that never appear in NBA player names — used to discard junk rows
_JUNK_WORDS = {
    'lines', 'basket', 'bets', 'promotions', 'privacy', 'policy',
    'points', 'threes', 'rebounds', 'assists', 'parlay', 'quick',
    'same', 'popular', 'home', 'game', 'first', 'made', 'player',
    'quarter', 'half', 'total', 'spread', 'moneyline', 'terms',
    'conditions', 'responsible', 'gambling', 'contact', 'help',
}

PLAYER_POINTS_TAB_XPATHS = [
    '//button[contains(text(),"Player Points")]',
    '//a[contains(text(),"Player Points")]',
    '//*[@role="tab" and contains(text(),"Player Points")]',
    '//span[contains(text(),"Player Points")]',
    '//*[contains(translate(text(),"abcdefghijklmnopqrstuvwxyz",'
    '"ABCDEFGHIJKLMNOPQRSTUVWXYZ"),"PLAYER POINTS")]',
]

SECTION_HEADER_XPATHS = [
    '//*[contains(text(),"To Score") and contains(text(),"+")]',
    '//*[contains(text(),"Score") and contains(text(),"+") and contains(text(),"Points")]',
]


def _is_valid_player_name(name: str) -> bool:
    """
    Return True only if the string looks like a real NBA player name.

    Rules:
    - 2–4 whitespace-separated tokens
    - Each token is alphabetic (hyphens OK for compound names like Karl-Anthony)
    - No token appears in the junk word set
    - At least one token ≥ 3 chars (not just initials)
    """
    name = name.strip()
    if not name or '\n' in name:
        return False
    tokens = name.split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    for tok in tokens:
        # Allow hyphens (e.g. Karl-Anthony)
        clean = tok.replace('-', '')
        if not clean.isalpha():
            return False
        if tok.lower() in _JUNK_WORDS:
            return False
    if not any(len(t) >= 3 for t in tokens):
        return False
    return True


class FanDuelScraper:

    def __init__(self):
        print("[FanDuel] Launching Chrome...")
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1400,900")
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = uc.Chrome(options=options, headless=False, version_main=147)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        self.wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)
        print("[FanDuel] Browser ready.")

    def _dismiss_popups(self):
        for sel in [
            "button[data-test='cookie-policy-dialog-accept-btn']",
            "[aria-label='Close']",
            "[data-test='close-button']",
            "button.sb-close-button",
            "[class*='CloseButton']",
            "[class*='close-button']",
            "[class*='dismiss']",
        ]:
            try:
                self.driver.find_element(By.CSS_SELECTOR, sel).click()
                time.sleep(0.3)
                print(f"[FanDuel] Dismissed popup: {sel}")
            except Exception:
                pass

    def _click_player_points_tab(self) -> bool:
        for xpath in PLAYER_POINTS_TAB_XPATHS:
            try:
                el = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", el
                )
                time.sleep(0.2)
                self.driver.execute_script("arguments[0].click();", el)
                print("[FanDuel] Clicked 'Player Points' tab")
                return True
            except Exception:
                continue
        print("[FanDuel] WARNING: Could not find 'Player Points' tab — proceeding anyway")
        return False

    def _find_section_headers(self) -> list:
        for xpath in SECTION_HEADER_XPATHS:
            els = self.driver.find_elements(By.XPATH, xpath)
            if els:
                print(f"[FanDuel] Found {len(els)} section headers")
                return els
        return []

    def _extract_players_from_section(
        self, section_el, threshold: int, line: str
    ) -> list:
        """
        After clicking a section header, find all valid player+odds rows
        within the smallest ancestor that contains expanded content.

        Uses strict name validation to discard navigation/category text.
        Limits ancestor traversal to 4 levels to stay near the section.
        """
        players = []

        for levels_up in range(1, 5):
            try:
                ancestor_xpath = "/".join([".."] * levels_up)
                container = section_el.find_element(By.XPATH, ancestor_xpath)

                # Find elements with odds-only text (4–5 chars, starts with +/-)
                odds_xpath = (
                    './/*['
                    'string-length(normalize-space(text())) >= 4 and '
                    'string-length(normalize-space(text())) <= 5 and '
                    '(starts-with(normalize-space(text()),"+") or '
                    'starts-with(normalize-space(text()),"-"))]'
                )
                odds_els = container.find_elements(By.XPATH, odds_xpath)

                for odds_el in odds_els:
                    try:
                        odds_text = odds_el.text.strip()
                        if not re.match(r'^[+\-]\d{3,4}$', odds_text):
                            continue

                        # Look at parent row for player name
                        for row_levels in range(1, 4):
                            try:
                                row_xpath = "/".join([".."] * row_levels)
                                row = odds_el.find_element(By.XPATH, row_xpath)
                                row_text = row.text.strip()

                                # Candidate name = row text minus the odds value
                                candidate = row_text.replace(odds_text, '').strip()
                                # Collapse any whitespace/newlines
                                candidate = re.sub(r'[\s\n\r]+', ' ', candidate).strip()

                                if _is_valid_player_name(candidate):
                                    players.append({
                                        "player": candidate,
                                        "line": line,
                                        "over_odds": odds_text,
                                        "under_odds": "N/A",
                                        "book": "fanduel",
                                        "game": GAME_LABEL,
                                        "timestamp": datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                    })
                                    break  # found valid name at this row level
                            except StaleElementReferenceException:
                                break
                            except Exception:
                                continue

                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue

                if players:
                    return players

            except Exception:
                continue

        return players

    def _handle_bot_challenge(self) -> bool:
        """
        Detect and wait out Cloudflare 'Press & Hold' or similar bot challenges.
        Returns True if a challenge was detected (regardless of resolution).
        """
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Press & Hold" in body_text or "confirm you are" in body_text.lower():
                print("[FanDuel] Bot challenge detected — waiting 15s for manual bypass...")
                time.sleep(15)
                return True
        except Exception:
            pass
        return False

    def get_player_props(self) -> list:
        print(f"[FanDuel] Loading: {config.FD_GAME_URL}")
        # Longer initial pause to let undetected_chromedriver fully initialize
        # before Cloudflare fingerprints the session
        time.sleep(3)
        self.driver.get(config.FD_GAME_URL)
        print("[FanDuel] Waiting 8s for page to load...")
        time.sleep(8)
        self._handle_bot_challenge()
        self._dismiss_popups()

        self._click_player_points_tab()
        time.sleep(2)
        self._dismiss_popups()

        headers = self._find_section_headers()
        if not headers:
            print("[FanDuel] No section headers found. Page snippet:")
            try:
                print(self.driver.find_element(By.TAG_NAME, "body").text[:600])
            except Exception:
                pass
            return []

        all_props = []
        num_headers = len(headers)

        for i in range(num_headers):
            try:
                # Re-fetch to avoid stale refs after each expand
                current_headers = self._find_section_headers()
                if i >= len(current_headers):
                    break

                section_el = current_headers[i]
                section_text = section_el.text.strip()

                thresh_match = re.search(r'(\d+)\+', section_text)
                if not thresh_match:
                    print(f"[FanDuel] Section {i+1} skipped (no threshold): '{section_text[:50]}'")
                    continue
                threshold = int(thresh_match.group(1))
                line = str(float(threshold) - 0.5)

                print(f"[FanDuel] Section {i+1}/{num_headers}: '{section_text[:50]}' → {threshold}+")

                # Scroll into view and click to expand
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center',behavior:'instant'});",
                    section_el,
                )
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", section_el)
                time.sleep(1.5)

                players = self._extract_players_from_section(section_el, threshold, line)
                if players:
                    print(f"[FanDuel]   → {len(players)} players: {[p['player'] for p in players]}")
                    all_props.extend(players)
                else:
                    print(f"[FanDuel]   → No valid players found")

            except StaleElementReferenceException:
                print(f"[FanDuel] Stale element at section {i+1}, skipping")
                continue
            except Exception as e:
                print(f"[FanDuel] Error on section {i+1}: {e}")
                continue

        # Deduplicate by (player, line)
        seen = set()
        unique = []
        for p in all_props:
            key = (p["player"].lower(), p["line"])
            if key not in seen:
                seen.add(key)
                unique.append(p)

        print(f"[FanDuel] Total unique props: {len(unique)}")
        return unique

    def close(self):
        try:
            self.driver.quit()
            print("[FanDuel] Browser closed.")
        except Exception:
            pass
