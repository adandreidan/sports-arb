import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

# The JS that walks text nodes
JS = """
var results = [];
var oddsRe = /^[+\\-]\\d{3,4}$/;
var toScoreRe = /To Score\\s+(\\d+)\\+/i;
var nameRe = /^[A-Z][a-z]+(?:[ \\-][A-Z][a-z]+){1,3}$/;
var walker = document.createTreeWalker(
    document.body, NodeFilter.SHOW_TEXT, null, false
);
var node;
while ((node = walker.nextNode())) {
    var t = node.textContent.trim();
    if (!oddsRe.test(t)) continue;
    var el = node.parentElement;
    for (var depth = 0; depth < 12 && el; depth++, el = el.parentElement) {
        var inner = (el.innerText || '').trim();
        if (!toScoreRe.test(inner)) continue;
        if (inner.length > 1000) break;
        var threshMatch = inner.match(toScoreRe);
        var threshold = parseInt(threshMatch[1]);
        var w2 = document.createTreeWalker(
            el, NodeFilter.SHOW_TEXT, null, false
        );
        var n2;
        while ((n2 = w2.nextNode())) {
            var nt = n2.textContent.trim();
            if (nameRe.test(nt)) {
                results.push({
                    odds: t,
                    player: nt,
                    threshold: threshold,
                    context: inner.substring(0, 200)
                });
                break;
            }
        }
        break;
    }
}
return results;
"""

# ALSO run a separate JS that just finds ALL odds on the page
# so we can see what odds numbers exist at all
JS_ALL_ODDS = """
var results = [];
var oddsRe = /^[+\\-]\\d{3,4}$/;
var walker = document.createTreeWalker(
    document.body, NodeFilter.SHOW_TEXT, null, false
);
var node;
while ((node = walker.nextNode())) {
    var t = node.textContent.trim();
    if (!oddsRe.test(t)) {
        continue;
    }
    var parent = node.parentElement;
    var parentText = (parent ? parent.innerText : '').trim().substring(0, 100);
    results.push({odds: t, parentText: parentText});
}
return results;
"""

# ALSO run a JS that finds all player names on the page
JS_ALL_NAMES = """
var results = [];
var nameRe = /^[A-Z][a-z]+(?:[ \\-][A-Z][a-z]+){1,3}$/;
var walker = document.createTreeWalker(
    document.body, NodeFilter.SHOW_TEXT, null, false
);
var node;
while ((node = walker.nextNode())) {
    var t = node.textContent.trim();
    if (nameRe.test(t)) {
        var parent = node.parentElement;
        var parentText = (parent ? parent.innerText : '').trim().substring(0, 100);
        results.push({name: t, parentText: parentText});
    }
}
return results;
"""

def debug_page(url, book_name):
    print(f"\n{'='*60}")
    print(f"DEBUGGING: {book_name}")
    print(f"URL: {url}")
    print(f"{'='*60}\n")

    driver = uc.Chrome(version_main=147)

    try:
        driver.get(url)
        print("Waiting 8 seconds for page to load...")
        time.sleep(8)

        # Click POINTS tab for DraftKings
        if "draftkings" in url:
            try:
                tab = driver.find_element(
                    By.XPATH,
                    '//*[normalize-space(.)="POINTS"]'
                )
                driver.execute_script("arguments[0].click();", tab)
                print("[DraftKings] Clicked POINTS tab")
                time.sleep(3)
            except Exception as e:
                print(f"[DraftKings] POINTS tab failed: {e}")

        # Click Player Points tab for FanDuel
        if "fanduel" in url:
            try:
                tab = driver.find_element(
                    By.XPATH,
                    '//*[normalize-space(text())="Player Points"]'
                )
                driver.execute_script("arguments[0].click();", tab)
                print("Clicked Player Points tab")
                time.sleep(3)
            except Exception as e:
                print(f"Could not click Player Points tab: {e}")

        # FIX 2 — DraftKings: expand collapsed sections after POINTS tab
        if "draftkings" in url:
            collapsed = driver.find_elements(
                By.XPATH, '//*[@aria-expanded="false"]'
            )
            print(f"[DraftKings] Expanding {len(collapsed)} sections")
            for el in collapsed:
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", el
                    )
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.3)
                except Exception:
                    pass
            time.sleep(2)

        # FIX 3 — FanDuel: expand ALL collapsed sections before scanning
        if "fanduel" in url:
            time.sleep(2)
            for attempt in range(3):
                collapsed = driver.find_elements(
                    By.XPATH, '//*[@aria-expanded="false"]'
                )
                if not collapsed:
                    break
                print(f"[FanDuel] Expanding {len(collapsed)} sections (attempt {attempt+1})")
                for el in collapsed:
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", el
                        )
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(0.2)
                    except Exception:
                        pass
                time.sleep(2)

        # Scroll down to load content
        print("Scrolling down...")
        for i in range(5):
            driver.execute_script(
                f"window.scrollTo(0, {(i+1) * 800});"
            )
            time.sleep(0.5)
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # STEP 1: Show ALL odds found on page
        print(f"\n--- ALL ODDS FOUND ON PAGE ---")
        all_odds = driver.execute_script(JS_ALL_ODDS)
        print(f"Total odds numbers found: {len(all_odds)}")
        for i, item in enumerate(all_odds[:20]):
            print(f"  Odds: {item['odds']:>6}  |  Parent text: {item['parentText'][:60]}")
        if len(all_odds) > 20:
            print(f"  ... and {len(all_odds) - 20} more")

        # STEP 2: Show ALL player names found on page
        print(f"\n--- ALL PLAYER NAMES FOUND ON PAGE ---")
        all_names = driver.execute_script(JS_ALL_NAMES)
        print(f"Total names found: {len(all_names)}")
        for i, item in enumerate(all_names[:20]):
            print(f"  Name: {item['name']:25}  |  Parent: {item['parentText'][:50]}")
        if len(all_names) > 20:
            print(f"  ... and {len(all_names) - 20} more")

        # STEP 3: Show what the main JS extraction finds
        print(f"\n--- MAIN JS EXTRACTION RESULTS ---")
        results = driver.execute_script(JS)
        print(f"Total matched player+odds pairs: {len(results)}")

        if results:
            print("\nMATCHED RESULTS:")
            for i, r in enumerate(results[:20]):
                print(f"\n  Result {i+1}:")
                print(f"    Player:    {r['player']}")
                print(f"    Threshold: {r['threshold']}+")
                print(f"    Odds:      {r['odds']}")
                print(f"    Context:   {r['context'][:100]}")
        else:
            print("NO MATCHES FOUND")
            print("\nThis means either:")
            print("  1. Player names and odds are not in same DOM container")
            print("  2. Page did not load properly")
            print("  3. Need to expand sections first")

            # Show raw page text so we can see what loaded
            print("\n--- PAGE TEXT SAMPLE (first 2000 chars) ---")
            body = driver.find_element(By.TAG_NAME, "body").text
            print(body[:2000])

        input("\nPress Enter to close browser...")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        driver.quit()

# Run debug on both books
debug_page(
    "https://sportsbook.draftkings.com/event/phi-76ers-%2540-ny-knicks/34103684",
    "DRAFTKINGS"
)

debug_page(
    "https://on.sportsbook.fanduel.ca/basketball/nba/philadelphia-76ers-@-new-york-knicks-35564245",
    "FANDUEL"
)
