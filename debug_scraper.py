import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import re
import time

# --- DraftKings JS ---
# Uses exact CSS classes from real_dk.html
# .cb-market__label--truncate-strings  → player name
# .cb-selection-picker__selection-label → threshold (e.g. "20+")
# .cb-selection-picker__selection-odds  → odds (e.g. "−105")
JS_DK = r"""
var results = [];
var rows = document.querySelectorAll('[data-testid="market-label"]');
for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var nameEl = row.querySelector('.cb-market__label--truncate-strings');
    if (!nameEl) continue;
    var player = nameEl.textContent.trim();
    if (!player || player.length < 3) continue;

    var buttons = row.querySelectorAll('.cb-selection-picker__selection');
    for (var j = 0; j < buttons.length; j++) {
        var btn = buttons[j];
        var labelEl = btn.querySelector('.cb-selection-picker__selection-label');
        var oddsEl  = btn.querySelector('.cb-selection-picker__selection-odds');
        if (!labelEl || !oddsEl) continue;

        var threshText = labelEl.textContent.trim();
        var oddsText   = oddsEl.textContent.trim();

        var threshMatch = threshText.match(/^(\d+)\+$/);
        if (!threshMatch) continue;

        results.push({
            player:    player,
            threshold: parseInt(threshMatch[1]),
            odds:      oddsText,
        });
    }
}
return results;
"""

# --- FanDuel JS ---
# After expanding sections, each bet row has:
#   aria-label="To Score 5+ Points, Josh Hart, -2200"
JS_FD = r"""
var results = [];
var re = /^To Score (\d+)\+ Points, (.+), ([+\-−]\d+)$/;
var buttons = document.querySelectorAll('[role="button"][aria-label]');
for (var i = 0; i < buttons.length; i++) {
    var label = buttons[i].getAttribute('aria-label') || '';
    var m = label.match(re);
    if (!m) continue;
    var player = m[2].trim();
    if (!player) continue;
    results.push({
        threshold: parseInt(m[1]),
        player:    player,
        odds:      m[3].trim(),
    });
}
return results;
"""


def debug_dk(url):
    print(f"\n{'='*60}")
    print(f"DEBUGGING: DRAFTKINGS")
    print(f"URL: {url}")
    print(f"{'='*60}\n")

    driver = uc.Chrome(version_main=147)
    try:
        driver.get(url)
        print("Waiting 6s for page load...")
        time.sleep(6)

        # Click POINTS tab
        tab_clicked = False
        try:
            el = driver.find_element(
                By.CSS_SELECTOR,
                'a[data-testid="tab-switcher-tab-inner"][href*="subcategory=points"]'
            )
            driver.execute_script("arguments[0].click();", el)
            print(f"[DK] Clicked POINTS tab via CSS selector (text='{el.text}')")
            tab_clicked = True
            time.sleep(2)
        except Exception:
            pass

        if not tab_clicked:
            for xpath in [
                '//*[translate(normalize-space(.),"abcdefghijklmnopqrstuvwxyz","ABCDEFGHIJKLMNOPQRSTUVWXYZ")="POINTS" and not(*)]',
                '//a[contains(@href,"subcategory=points")]',
            ]:
                try:
                    el = driver.find_element(By.XPATH, xpath)
                    driver.execute_script("arguments[0].click();", el)
                    print(f"[DK] Clicked POINTS tab via XPath fallback")
                    time.sleep(2)
                    tab_clicked = True
                    break
                except Exception:
                    continue

        if not tab_clicked:
            print("[DK] WARNING: POINTS tab not found")

        # First scroll pass — forces lazy-loaded content to render
        print("[DK] First scroll pass to load POINTS content...")
        pos = 0
        while True:
            total = driver.execute_script("return document.body.scrollHeight")
            if pos >= total:
                break
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(0.35)
            pos += 400
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Expand all collapsed sections (only those with aria-expanded attribute,
        # meaning they are genuine accordion/section toggles)
        collapsed = driver.find_elements(By.XPATH, '//*[@aria-expanded="false"]')
        print(f"[DK] Expanding {len(collapsed)} collapsed sections...")
        for el in collapsed:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center',behavior:'instant'});", el
                )
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.2)
            except Exception:
                pass
        time.sleep(2)

        # Second scroll pass — forces newly expanded content to render
        print("[DK] Second scroll pass after expansion...")
        pos = 0
        while True:
            total = driver.execute_script("return document.body.scrollHeight")
            if pos >= total:
                break
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(0.35)
            pos += 400
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Diagnostics: count key elements before running main JS
        n_market = driver.execute_script(
            "return document.querySelectorAll('[data-testid=\"market-label\"]').length;"
        )
        n_name = driver.execute_script(
            "return document.querySelectorAll('.cb-market__label--truncate-strings').length;"
        )
        n_picker = driver.execute_script(
            "return document.querySelectorAll('.cb-selection-picker__selection').length;"
        )
        n_odds = driver.execute_script(
            "return document.querySelectorAll('.cb-selection-picker__selection-odds').length;"
        )
        print(f"[DK] DOM counts: market-label={n_market}  player-name={n_name}  picker-btn={n_picker}  odds={n_odds}")

        # If no market-label rows, try scrolling/waiting more and re-checking
        if n_market == 0:
            print("[DK] No market-label rows found. Waiting 5s more and retrying scroll...")
            time.sleep(5)
            pos = 0
            while True:
                total = driver.execute_script("return document.body.scrollHeight")
                if pos >= total:
                    break
                driver.execute_script(f"window.scrollTo(0, {pos});")
                time.sleep(0.4)
                pos += 400
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            n_market = driver.execute_script(
                "return document.querySelectorAll('[data-testid=\"market-label\"]').length;"
            )
            n_name = driver.execute_script(
                "return document.querySelectorAll('.cb-market__label--truncate-strings').length;"
            )
            print(f"[DK] After retry: market-label={n_market}  player-name={n_name}")

        # Show all data-testid values present on page (first 30 unique)
        testids = driver.execute_script("""
            var ids = {};
            document.querySelectorAll('[data-testid]').forEach(function(el) {
                ids[el.getAttribute('data-testid')] = true;
            });
            return Object.keys(ids).slice(0, 40);
        """)
        print(f"[DK] All data-testid values on page ({len(testids)}):")
        for tid in testids:
            print(f"  {tid}")

        # Run extraction
        raw = driver.execute_script(JS_DK)
        print(f"\n[DK] JS found {len(raw or [])} raw results")

        if raw:
            print(f"\n{'Player':<30} {'Threshold':>10} {'Odds':>8}")
            print(f"{'-'*30} {'-'*10} {'-'*8}")
            for r in sorted(raw, key=lambda x: (x['player'], x['threshold'])):
                odds = r['odds'].replace('−', '-')
                print(f"{r['player']:<30} {str(r['threshold'])+'+':>10} {odds:>8}")
        else:
            print("[DK] NO RESULTS")
            body = driver.find_element(By.TAG_NAME, "body").text
            print("Page sample:", body[:1000])

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()


def debug_fd(url):
    print(f"\n{'='*60}")
    print(f"DEBUGGING: FANDUEL")
    print(f"URL: {url}")
    print(f"{'='*60}\n")

    driver = uc.Chrome(version_main=147)
    try:
        # Navigate directly to Player Points tab
        tab_url = url.rstrip('/') + "?tab=player-points"
        time.sleep(2)
        driver.get(tab_url)
        print("Waiting 8s for page load...")
        time.sleep(8)

        # Bot challenge check — wait up to 30s for manual solve
        for attempt in range(3):
            try:
                body = driver.find_element(By.TAG_NAME, "body").text
                if "Press & Hold" in body or "confirm you are" in body.lower():
                    print(f"[FD] Bot challenge detected (attempt {attempt+1}) — waiting 30s for manual solve...")
                    time.sleep(30)
                else:
                    break
            except Exception:
                break

        # Expand all collapsed 'To Score X+ Points' sections
        sections = driver.find_elements(By.CSS_SELECTOR, '[role="button"][aria-expanded="false"]')
        to_score = [
            el for el in sections
            if re.match(r'^To Score \d+\+ Points$',
                        (el.get_attribute('aria-label') or '').strip())
        ]
        print(f"[FD] Found {len(to_score)} collapsed 'To Score X+' sections")
        for el in to_score:
            try:
                label = el.get_attribute('aria-label')
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center',behavior:'instant'});", el
                )
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", el)
                time.sleep(1.0)
                print(f"[FD]   Expanded: {label}")
            except Exception:
                pass
        time.sleep(2)

        # Scroll through page to force lazy-loaded bet rows to render
        print("[FD] Scrolling to trigger lazy-loaded content...")
        pos = 0
        while True:
            total = driver.execute_script("return document.body.scrollHeight")
            if pos >= total:
                break
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(0.4)
            pos += 400
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Run extraction
        raw = driver.execute_script(JS_FD)
        print(f"\n[FD] JS found {len(raw or [])} raw results")

        if raw:
            print(f"\n{'Player':<30} {'Threshold':>10} {'Odds':>8}")
            print(f"{'-'*30} {'-'*10} {'-'*8}")
            for r in sorted(raw, key=lambda x: (x['threshold'], x['player'])):
                odds = r['odds'].replace('−', '-')
                print(f"{r['player']:<30} {str(r['threshold'])+'+':>10} {odds:>8}")
        else:
            print("[FD] NO RESULTS")
            body = driver.find_element(By.TAG_NAME, "body").text
            print("Page sample:", body[:1000])

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()


debug_dk("https://sportsbook.draftkings.com/event/phi-76ers-%2540-ny-knicks/34103684")
debug_fd("https://on.sportsbook.fanduel.ca/basketball/nba/philadelphia-76ers-@-new-york-knicks-35564245")
