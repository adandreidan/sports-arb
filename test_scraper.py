# test_scraper.py — Run both scrapers against real game URLs and print every result

import sys
from datetime import datetime

from scraper_draftkings import DraftKingsScraper
from scraper_fanduel import FanDuelScraper
import config


def print_props(props: list, book: str) -> None:
    if not props:
        print(f"\n  *** {book.upper()}: No props found ***")
        return
    print(f"\n  {book.upper()} — {len(props)} props found:")
    print(f"  {'Player':<30} {'Line':>6}  {'Over Odds':>10}")
    print(f"  {'-'*30} {'-'*6}  {'-'*10}")
    for p in sorted(props, key=lambda x: (x["line"], x["player"])):
        print(f"  {p['player']:<30} {p['line']:>6}  {p['over_odds']:>10}")


def test_draftkings() -> list:
    print("\n" + "=" * 60)
    print("TEST: DRAFTKINGS")
    print(f"URL: {config.DK_GAME_URL}")
    print("=" * 60)

    scraper = None
    try:
        scraper = DraftKingsScraper()
        props = scraper.get_player_props()
        print_props(props, "DraftKings")
        return props
    except Exception as e:
        print(f"[DK TEST ERROR] {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if scraper:
            scraper.close()


def test_fanduel() -> list:
    print("\n" + "=" * 60)
    print("TEST: FANDUEL")
    print(f"URL: {config.FD_GAME_URL}")
    print("=" * 60)

    scraper = None
    try:
        scraper = FanDuelScraper()
        props = scraper.get_player_props()
        print_props(props, "FanDuel")
        return props
    except Exception as e:
        print(f"[FD TEST ERROR] {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if scraper:
            scraper.close()


def test_matching(dk_props: list, fd_props: list) -> None:
    print("\n" + "=" * 60)
    print("MATCHING — players found on both books at same threshold")
    print("=" * 60)

    if not dk_props or not fd_props:
        print("  Cannot match: one or both scrapers returned no props.")
        return

    # Build lookup: (name_lower, line) -> dk prop
    dk_lookup = {}
    for p in dk_props:
        dk_lookup[(p["player"].lower(), p["line"])] = p

    matched = 0
    for fd in fd_props:
        key = (fd["player"].lower(), fd["line"])
        if key in dk_lookup:
            dk = dk_lookup[key]
            print(f"  MATCH  {fd['player']:<28}  line={fd['line']:>5}  "
                  f"FD={fd['over_odds']:>6}  DK={dk['over_odds']:>6}")
            matched += 1

    if matched == 0:
        print("  No exact matches found.")
        print("  (Names may differ slightly between books — check printouts above)")
    else:
        print(f"\n  Total matched: {matched}")


if __name__ == "__main__":
    print("=" * 60)
    print("SCRAPER TEST — Real Game URLs")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    dk_props = test_draftkings()
    fd_props = test_fanduel()
    test_matching(dk_props, fd_props)

    print("\n" + "=" * 60)
    print(f"DONE  |  DraftKings: {len(dk_props)} props  |  FanDuel: {len(fd_props)} props")
    print("=" * 60)
