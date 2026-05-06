# main.py — Main orchestrator for the sports arbitrage scanner

import sys
import threading
import time
from datetime import datetime

import arb_calculator
import alerter
import config
import logger
from scraper_fanduel import FanDuelScraper
from scraper_draftkings import DraftKingsScraper


def scrape_fanduel(results: dict) -> None:
    """
    Thread worker: scrape all FanDuel NBA props and store in results dict.

    Called in a thread so FanDuel and DraftKings can scrape simultaneously.
    Stores the list of props under results['fanduel'].

    Args:
        results: Shared dict where results will be written
    """
    try:
        scraper = FanDuelScraper()
        props = scraper.get_all_props()
        results["fanduel"] = props
        scraper.close()
    except Exception as e:
        print(f"[main] FanDuel scraper thread error: {e}")
        results["fanduel"] = []


def scrape_draftkings(results: dict) -> None:
    """
    Thread worker: scrape all DraftKings NBA props and store in results dict.

    Called in a thread so FanDuel and DraftKings can scrape simultaneously.
    Stores the list of props under results['draftkings'].

    Args:
        results: Shared dict where results will be written
    """
    try:
        scraper = DraftKingsScraper()
        props = scraper.get_all_props()
        results["draftkings"] = props
        scraper.close()
    except Exception as e:
        print(f"[main] DraftKings scraper thread error: {e}")
        results["draftkings"] = []


def match_props(fd_props: list, dk_props: list) -> list:
    """
    Find players who appear in BOTH FanDuel and DraftKings with the SAME threshold.

    Both books use "To Score X+" format so the line is derived identically
    (threshold - 0.5), making the line value the canonical match key.

    Matching criteria:
        - Player name match (case-insensitive, last-name fallback)
        - Same line value (e.g. "24.5" means both books have a 25+ threshold)
    """
    matches = []

    # Build lookup: (player_name_lower, line) -> dk prop
    dk_lookup = {}
    for prop in dk_props:
        key = (prop["player"].lower().strip(), prop["line"].strip())
        dk_lookup[key] = prop

    # Also build last-name-only lookup for fuzzy matching
    dk_lastname_lookup = {}
    for prop in dk_props:
        parts = prop["player"].lower().strip().split()
        if parts:
            key = (parts[-1], prop["line"].strip())
            dk_lastname_lookup.setdefault(key, prop)

    for fd_prop in fd_props:
        fd_name = fd_prop["player"].lower().strip()
        fd_line = fd_prop["line"].strip()

        # Exact match
        exact_key = (fd_name, fd_line)
        if exact_key in dk_lookup:
            matches.append({
                "player": fd_prop["player"],
                "line": fd_line,
                "fd_prop": fd_prop,
                "dk_prop": dk_lookup[exact_key],
            })
            continue

        # Last-name fallback
        parts = fd_name.split()
        if parts:
            lastname_key = (parts[-1], fd_line)
            if lastname_key in dk_lastname_lookup:
                dk_prop = dk_lastname_lookup[lastname_key]
                matches.append({
                    "player": fd_prop["player"],
                    "line": fd_line,
                    "fd_prop": fd_prop,
                    "dk_prop": dk_prop,
                })

    return matches


def find_arbs(matches: list, scan_number: int) -> int:
    """
    Check each matched player/line pair for arbitrage opportunities.

    For each match, compares FanDuel's Over odds vs DraftKings' Over odds
    and FanDuel's Under odds vs DraftKings' Under odds.

    When an arb is found:
        - Prints a terminal alert via alerter.print_alert()
        - Sends Discord alert via alerter.send_discord_alert() (if configured)
        - Logs to CSV via logger.log_arb()

    Args:
        matches: List of matched prop dicts from match_props()
        scan_number: Current scan iteration number (for display only)

    Returns:
        Number of arbs found in this scan.
    """
    arbs_found = 0

    for match in matches:
        player = match["player"]
        line = match["line"]
        fd = match["fd_prop"]
        dk = match["dk_prop"]

        # ── Compare FanDuel Over vs DraftKings Under ───────────────────────────
        # (Bet Over on FanDuel, Under on DraftKings)
        if fd["over_odds"] != "N/A" and dk["under_odds"] != "N/A":
            try:
                result = arb_calculator.check_arb(
                    int(fd["over_odds"]), int(dk["under_odds"])
                )
                if result["arb_exists"]:
                    stakes = arb_calculator.calculate_stakes(
                        int(fd["over_odds"]), int(dk["under_odds"]), config.BANKROLL
                    )
                    profit = arb_calculator.calculate_guaranteed_profit(
                        int(fd["over_odds"]), int(dk["under_odds"]), config.BANKROLL
                    )
                    alerter.print_alert(
                        player=player, prop=config.PROP_TYPE, line=line,
                        book1="fanduel", odds1=fd["over_odds"], stake1=stakes["stake1"],
                        book2="draftkings", odds2=dk["under_odds"], stake2=stakes["stake2"],
                        profit_pct=result["profit_pct"], guaranteed_profit=profit,
                    )
                    alerter.send_discord_alert(
                        player=player, prop=config.PROP_TYPE, line=line,
                        book1="fanduel", odds1=fd["over_odds"], stake1=stakes["stake1"],
                        book2="draftkings", odds2=dk["under_odds"], stake2=stakes["stake2"],
                        profit_pct=result["profit_pct"], guaranteed_profit=profit,
                    )
                    logger.log_arb(
                        player=player, prop=config.PROP_TYPE, line=line,
                        book1="fanduel", odds1=fd["over_odds"], stake1=stakes["stake1"],
                        book2="draftkings", odds2=dk["under_odds"], stake2=stakes["stake2"],
                        profit_pct=result["profit_pct"], guaranteed_profit=profit,
                    )
                    arbs_found += 1
            except (ValueError, TypeError) as e:
                print(f"[main] Skipping invalid odds for {player} (FD over vs DK under): {e}")

        # ── Compare FanDuel Under vs DraftKings Over ───────────────────────────
        # (Bet Under on FanDuel, Over on DraftKings)
        if fd["under_odds"] != "N/A" and dk["over_odds"] != "N/A":
            try:
                result = arb_calculator.check_arb(
                    int(fd["under_odds"]), int(dk["over_odds"])
                )
                if result["arb_exists"]:
                    stakes = arb_calculator.calculate_stakes(
                        int(fd["under_odds"]), int(dk["over_odds"]), config.BANKROLL
                    )
                    profit = arb_calculator.calculate_guaranteed_profit(
                        int(fd["under_odds"]), int(dk["over_odds"]), config.BANKROLL
                    )
                    alerter.print_alert(
                        player=player, prop=config.PROP_TYPE, line=line,
                        book1="fanduel", odds1=fd["under_odds"], stake1=stakes["stake1"],
                        book2="draftkings", odds2=dk["over_odds"], stake2=stakes["stake2"],
                        profit_pct=result["profit_pct"], guaranteed_profit=profit,
                    )
                    alerter.send_discord_alert(
                        player=player, prop=config.PROP_TYPE, line=line,
                        book1="fanduel", odds1=fd["under_odds"], stake1=stakes["stake1"],
                        book2="draftkings", odds2=dk["over_odds"], stake2=stakes["stake2"],
                        profit_pct=result["profit_pct"], guaranteed_profit=profit,
                    )
                    logger.log_arb(
                        player=player, prop=config.PROP_TYPE, line=line,
                        book1="fanduel", odds1=fd["under_odds"], stake1=stakes["stake1"],
                        book2="draftkings", odds2=dk["over_odds"], stake2=stakes["stake2"],
                        profit_pct=result["profit_pct"], guaranteed_profit=profit,
                    )
                    arbs_found += 1
            except (ValueError, TypeError) as e:
                print(f"[main] Skipping invalid odds for {player} (FD under vs DK over): {e}")

    return arbs_found


def run_scan(scan_number: int) -> None:
    """
    Execute one full scan: scrape both books in parallel, match props, find arbs.

    Uses threading to run FanDuel and DraftKings scrapers simultaneously,
    halving the total scrape time.

    Args:
        scan_number: Current iteration count (printed at scan start)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print(f"  SCAN #{scan_number} — {timestamp}")
    print("=" * 60)

    # Shared dict for thread results
    results = {"fanduel": [], "draftkings": []}

    # Launch both scrapers in parallel threads
    print("[main] Launching FanDuel and DraftKings scrapers simultaneously...")
    fd_thread = threading.Thread(target=scrape_fanduel, args=(results,), daemon=True)
    dk_thread = threading.Thread(target=scrape_draftkings, args=(results,), daemon=True)

    fd_thread.start()
    dk_thread.start()

    # Wait for both to finish
    fd_thread.join()
    dk_thread.join()

    fd_props = results["fanduel"]
    dk_props = results["draftkings"]

    print(f"\n[main] FanDuel props collected : {len(fd_props)}")
    print(f"[main] DraftKings props collected: {len(dk_props)}")

    # Match players across both books
    matches = match_props(fd_props, dk_props)
    print(f"[main] Players matched across books: {len(matches)}")

    # Check each match for arb opportunities
    arbs = find_arbs(matches, scan_number)
    print(f"[main] Arbs found this scan: {arbs}")

    if arbs == 0:
        print("[main] No arbs found in this scan.")


def main() -> None:
    """
    Main entry point — runs the scanner in an infinite loop.

    Each iteration:
        1. Scrapes FanDuel and DraftKings simultaneously
        2. Matches players and lines
        3. Checks for arbitrage
        4. Sleeps for SCAN_INTERVAL seconds before repeating

    Handles KeyboardInterrupt (Ctrl+C) cleanly by printing a final summary.
    """
    print("=" * 60)
    print("  SPORTS ARB SCANNER — STARTING")
    print(f"  Sport     : {config.SPORT}")
    print(f"  Prop type : {config.PROP_TYPE}")
    print(f"  Bankroll  : ${config.BANKROLL}")
    print(f"  Interval  : {config.SCAN_INTERVAL}s")
    print("=" * 60)

    scan_number = 0

    try:
        while True:
            scan_number += 1
            run_scan(scan_number)
            print(f"\n[main] Sleeping {config.SCAN_INTERVAL}s before next scan...")
            time.sleep(config.SCAN_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[main] Interrupted by user (Ctrl+C). Shutting down...")
        logger.log_summary()
        print("[main] Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
