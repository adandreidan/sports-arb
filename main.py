import sys
import time
from datetime import datetime

import arb_calculator
import alerter
import config
import logger
from scraper_fanduel import FanDuelScraper
from scraper_draftkings import DraftKingsScraper


def switch_to_tab(driver, url_fragment: str) -> bool:
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if url_fragment in driver.current_url:
            return True
    print(f"[main] Could not find tab matching: {url_fragment}")
    return False


def match_props(fd_props: list, dk_props: list) -> list:
    dk_lookup = {(p["player"].lower(), p["line"]): p for p in dk_props}
    matches = []
    for fd in fd_props:
        key = (fd["player"].lower(), fd["line"])
        if key in dk_lookup:
            matches.append({
                "player": fd["player"],
                "line": fd["line"],
                "fd_prop": fd,
                "dk_prop": dk_lookup[key],
            })
    return matches


def find_arbs(matches: list) -> int:
    arbs_found = 0
    for match in matches:
        player = match["player"]
        line = match["line"]
        fd = match["fd_prop"]
        dk = match["dk_prop"]

        try:
            result = arb_calculator.check_arb(int(fd["over_odds"]), int(dk["over_odds"]))
            if result["arb_exists"]:
                stakes = arb_calculator.calculate_stakes(
                    int(fd["over_odds"]), int(dk["over_odds"]), config.BANKROLL
                )
                profit = arb_calculator.calculate_guaranteed_profit(
                    int(fd["over_odds"]), int(dk["over_odds"]), config.BANKROLL
                )
                alerter.print_alert(
                    player=player, prop=config.PROP_TYPE, line=line,
                    book1="fanduel", odds1=fd["over_odds"], stake1=stakes["stake1"],
                    book2="draftkings", odds2=dk["over_odds"], stake2=stakes["stake2"],
                    profit_pct=result["profit_pct"], guaranteed_profit=profit,
                )
                alerter.send_discord_alert(
                    player=player, prop=config.PROP_TYPE, line=line,
                    book1="fanduel", odds1=fd["over_odds"], stake1=stakes["stake1"],
                    book2="draftkings", odds2=dk["over_odds"], stake2=stakes["stake2"],
                    profit_pct=result["profit_pct"], guaranteed_profit=profit,
                )
                logger.log_arb(
                    player=player, prop=config.PROP_TYPE, line=line,
                    book1="fanduel", odds1=fd["over_odds"], stake1=stakes["stake1"],
                    book2="draftkings", odds2=dk["over_odds"], stake2=stakes["stake2"],
                    profit_pct=result["profit_pct"], guaranteed_profit=profit,
                )
                arbs_found += 1
        except (ValueError, TypeError) as e:
            print(f"[main] Skipping {player}: {e}")

    return arbs_found


def run_scan(fd_scraper: FanDuelScraper, dk_scraper: DraftKingsScraper, scan_number: int) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  SCAN #{scan_number} — {timestamp}")
    print(f"{'='*60}")

    fd_props = []
    if switch_to_tab(fd_scraper.driver, "fanduel"):
        print("[main] Scraping FanDuel...")
        fd_props = fd_scraper.get_player_props()

    dk_props = []
    if switch_to_tab(fd_scraper.driver, "draftkings"):
        print("[main] Scraping DraftKings...")
        dk_props = dk_scraper.get_player_props()

    print(f"\n[main] FanDuel props    : {len(fd_props)}")
    print(f"[main] DraftKings props : {len(dk_props)}")

    matches = match_props(fd_props, dk_props)
    print(f"[main] Matched players  : {len(matches)}")

    arbs = find_arbs(matches)
    print(f"[main] Arbs found       : {arbs}")
    if arbs == 0:
        print("[main] No arbs found this scan.")


def main() -> None:
    print("=" * 60)
    print("  SPORTS ARB SCANNER — STARTING")
    print(f"  Sport    : {config.SPORT}")
    print(f"  Prop     : {config.PROP_TYPE}")
    print(f"  Bankroll : ${config.BANKROLL}")
    print(f"  Interval : {config.SCAN_INTERVAL}s")
    print("=" * 60)

    fd_scraper = FanDuelScraper()
    dk_scraper = DraftKingsScraper()

    scan_number = 0
    try:
        while True:
            scan_number += 1
            run_scan(fd_scraper, dk_scraper, scan_number)
            print(f"\n[main] Sleeping {config.SCAN_INTERVAL}s before next scan...")
            time.sleep(config.SCAN_INTERVAL)
    except KeyboardInterrupt:
        print("\n[main] Interrupted. Shutting down...")
        logger.log_summary()
        print("[main] Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
