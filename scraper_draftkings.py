# scraper_draftkings.py

import re
import time
from datetime import datetime

import undetected_chromedriver as uc
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import config

GAME_LABEL = "PHI 76ers @ NY Knicks"

_JUNK_WORDS = {
    'lines', 'basket', 'bets', 'promotions', 'privacy', 'policy',
    'points', 'threes', 'rebounds', 'assists', 'parlay', 'quick',
    'same', 'popular', 'home', 'game', 'first', 'made', 'player',
    'quarter', 'half', 'total', 'spread', 'moneyline', 'mode',
    'surge', 'burner', 'bounce', 'back', 'problem', 'take',
    'rookies', 'combo', 'boost', 'promo', 'featured', 'trending',
}


def _is_valid_player_name(name: str) -> bool:
    if not name or '\n' in name:
        return False
    tokens = name.strip().split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    for tok in tokens:
        clean = tok.replace('-', '')
        if not clean.isalpha():
            return False
        if tok.lower() in _JUNK_WORDS:
            return False
    if not any(len(t) >= 3 for t in tokens):
        return False
    return True


# JS: walk every text node looking for American-odds strings,
# then walk up ancestors to find a player name + To Score threshold.
# Only accepts results where the ancestor container includes "To Score".
_JS_EXTRACT = r"""
var results = [];
var oddsRe = /^[+\-]\d{3,4}$/;
var toScoreRe = /To Score\s+(\d+)\+/i;
var nameRe = /^[A-Z][a-z]+(?:[ \-][A-Z][a-z]+){1,3}$/;

var walker = document.createTreeWalker(
    document.body, NodeFilter.SHOW_TEXT, null, false
);
var node;
while ((node = walker.nextNode())) {
    var t = node.textContent.trim();
    if (!oddsRe.test(t)) continue;

    // Walk up to find smallest ancestor with "To Score X+" text
    var el = node.parentElement;
    for (var depth = 0; depth < 12 && el; depth++, el = el.parentElement) {
        var inner = (el.innerText || '').trim();
        if (!toScoreRe.test(inner)) continue;
        if (inner.length > 1000) break;  // too broad

        var threshMatch = inner.match(toScoreRe);
        var threshold = parseInt(threshMatch[1]);

        // Walk text nodes inside this container to find a player name
        var w2 = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        var n2;
        while ((n2 = w2.nextNode())) {
            var nt = n2.textContent.trim();
            if (nameRe.test(nt)) {
                results.push({odds: t, player: nt, threshold: threshold});
                break;
            }
        }
        break;
    }
}
return results;
"""


class DraftKingsScraper:

    def __init__(self):
        print("[DraftKings] Launching Chrome...")
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1400,900")
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = uc.Chrome(options=options, headless=False, version_main=147)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        self.wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)
        print("[DraftKings] Browser ready.")

    def _dismiss_popups(self):
        for sel in [
            "button[id='onetrust-accept-btn-handler']",
            "[aria-label='Close']",
            "[data-testid='close-button']",
            "button.sportsbook-dialog__close",
            ".modal-close",
            "[class*='CloseButton']",
        ]:
            try:
                self.driver.find_element(By.CSS_SELECTOR, sel).click()
                time.sleep(0.3)
                print(f"[DraftKings] Dismissed popup: {sel}")
            except Exception:
                pass

    def _slow_scroll(self):
        pos, step = 0, 400
        while True:
            total = self.driver.execute_script("return document.body.scrollHeight")
            if pos >= total:
                break
            self.driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(0.35)
            pos += step
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

    def _click_points_tab(self) -> bool:
        """
        Click the 'POINTS' category tab within the DK game page.

        DraftKings game pages have tabs: ALL | POPULAR | GAME LINES | QUICK HITS
        | POINTS | THREES | REBOUNDS | ASSISTS | COMBOS ...
        The player scoring props are under 'POINTS'.
        """
        xpaths = [
            '//button[normalize-space(text())="POINTS"]',
            '//button[normalize-space(text())="Points"]',
            '//*[@role="tab" and normalize-space(text())="POINTS"]',
            '//*[@role="tab" and normalize-space(text())="Points"]',
            '//button[contains(@class,"tab") and normalize-space(text())="POINTS"]',
            '//a[normalize-space(text())="POINTS"]',
        ]
        for xpath in xpaths:
            try:
                el = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", el
                )
                time.sleep(0.2)
                self.driver.execute_script("arguments[0].click();", el)
                print(f"[DraftKings] Clicked 'POINTS' tab via {xpath[:60]}")
                return True
            except Exception:
                continue
        print("[DraftKings] WARNING: 'POINTS' tab not found — will try anyway")
        return False

    def _expand_sections(self):
        """Expand all 'To Score X+ Points' accordion sections."""
        xpaths = [
            '//*[contains(text(),"To Score") and contains(text(),"+") and contains(text(),"Points")]',
            '//*[contains(text(),"To Score") and contains(text(),"+")]',
            # Fallback: any aria-expanded=false element
        ]

        seen = set()
        clicked = 0

        for xpath in xpaths:
            els = self.driver.find_elements(By.XPATH, xpath)
            print(f"[DraftKings] Expand candidates: {len(els)} from '{xpath[:60]}...'")
            for el in els:
                try:
                    # Click the element and its parent (one of them should be the toggle)
                    for target_levels in range(0, 3):
                        t = el
                        for _ in range(target_levels):
                            t = t.find_element(By.XPATH, "..")
                        eid = self.driver.execute_script("return arguments[0].outerHTML.slice(0,80);", t)
                        if eid in seen:
                            continue
                        seen.add(eid)
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center',behavior:'instant'});", t
                        )
                        time.sleep(0.15)
                        self.driver.execute_script("arguments[0].click();", t)
                        time.sleep(0.4)
                        clicked += 1
                except Exception:
                    pass

        # Also click aria-expanded=false elements
        collapsed = self.driver.find_elements(By.XPATH, '//*[@aria-expanded="false"]')
        print(f"[DraftKings] aria-expanded=false: {len(collapsed)}")
        for el in collapsed:
            try:
                eid = self.driver.execute_script("return arguments[0].outerHTML.slice(0,80);", el)
                if eid in seen:
                    continue
                seen.add(eid)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center',behavior:'instant'});", el
                )
                time.sleep(0.15)
                self.driver.execute_script("arguments[0].click();", el)
                time.sleep(0.4)
                clicked += 1
            except Exception:
                pass

        print(f"[DraftKings] Clicked {clicked} expand targets")
        time.sleep(2)

    def _raw_to_prop(self, raw: dict) -> dict | None:
        player = (raw.get("player") or "").strip()
        threshold = raw.get("threshold")
        odds = (raw.get("odds") or "").strip()
        if not _is_valid_player_name(player):
            return None
        if not threshold or not re.match(r'^[+\-]\d{3,4}$', odds):
            return None
        return {
            "player": player,
            "line": str(float(threshold) - 0.5),
            "over_odds": odds,
            "under_odds": "N/A",
            "book": "draftkings",
            "game": GAME_LABEL,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _deduplicate(self, props: list) -> list:
        seen, unique = set(), []
        for p in props:
            key = (p["player"].lower(), p["line"])
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    def get_player_props(self) -> list:
        print(f"[DraftKings] Loading: {config.DK_GAME_URL}")
        self.driver.get(config.DK_GAME_URL)
        print("[DraftKings] Waiting 5s...")
        time.sleep(5)
        self._dismiss_popups()

        # Click 'POINTS' tab to show player scoring props section
        self._click_points_tab()
        time.sleep(2)
        self._dismiss_popups()

        print("[DraftKings] Scrolling to load all content...")
        self._slow_scroll()

        # Expand all collapsed sections
        self._expand_sections()

        # JS extraction: text-node walk scoped to 'To Score' containers
        print("[DraftKings] Running JS text-node extraction...")
        raw = self.driver.execute_script(_JS_EXTRACT)
        print(f"[DraftKings] JS found {len(raw or [])} raw results")

        props = []
        for r in (raw or []):
            p = self._raw_to_prop(r)
            if p:
                props.append(p)

        if not props:
            print("[DraftKings] JS scan found nothing. Page body sample:")
            try:
                body = self.driver.find_element(By.TAG_NAME, "body").text
                print(body[:2000])
            except Exception:
                pass

        unique = self._deduplicate(props)
        print(f"[DraftKings] Total unique props: {len(unique)}")
        return unique

    def close(self):
        try:
            self.driver.quit()
            print("[DraftKings] Browser closed.")
        except Exception:
            pass
