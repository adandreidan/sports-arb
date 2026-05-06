# arb_calculator.py — Math engine for detecting and sizing arbitrage bets

import config


def american_to_implied(odds: int) -> float:
    """
    Convert American odds (e.g. -110, +130) to implied probability (0.0 to 1.0).

    For negative odds (favorites):  prob = |odds| / (|odds| + 100)
    For positive odds (underdogs):  prob = 100 / (odds + 100)

    Returns implied probability as a float, or 0.0 on error.
    """
    try:
        odds = int(odds)
        if odds < 0:
            return abs(odds) / (abs(odds) + 100)
        else:
            return 100 / (odds + 100)
    except (ValueError, ZeroDivisionError) as e:
        print(f"[arb_calculator] Error converting odds {odds}: {e}")
        return 0.0


def check_arb(odds1: int, odds2: int) -> dict:
    """
    Determine whether two opposing odds create an arbitrage opportunity.

    An arbitrage exists when the sum of implied probabilities for both sides
    is LESS than 1.0, meaning you can bet both sides and guarantee a profit.

    Args:
        odds1: American odds for side 1 (e.g. Over at -114)
        odds2: American odds for side 2 (e.g. Under at +130)

    Returns a dict with:
        arb_exists    — True if this is a genuine arb opportunity
        profit_pct    — Guaranteed profit as a decimal (e.g. 0.039 = 3.9%)
        total_implied — Sum of both implied probabilities (< 1.0 means arb)
    """
    try:
        implied1 = american_to_implied(odds1)
        implied2 = american_to_implied(odds2)

        if implied1 == 0.0 or implied2 == 0.0:
            return {"arb_exists": False, "profit_pct": 0.0, "total_implied": 1.0}

        total_implied = implied1 + implied2
        profit_pct = 1 - total_implied  # positive means guaranteed profit

        arb_exists = (
            profit_pct > config.LOWER_LIMIT and profit_pct < config.UPPER_LIMIT
        )

        return {
            "arb_exists": arb_exists,
            "profit_pct": round(profit_pct, 4),
            "total_implied": round(total_implied, 4),
        }
    except Exception as e:
        print(f"[arb_calculator] Error in check_arb({odds1}, {odds2}): {e}")
        return {"arb_exists": False, "profit_pct": 0.0, "total_implied": 1.0}


def calculate_stakes(odds1: int, odds2: int, bankroll: float) -> dict:
    """
    Calculate how much to bet on each side so that profit is equal regardless
    of which side wins (Kelly-neutral equal-profit split).

    Formula derivation:
        Let stake1 + stake2 = bankroll
        payout1 = stake1 * (1 + 100/|odds1|) for negative odds,
                  stake1 * (1 + odds1/100) for positive odds
        We want payout1 == payout2
        => stake1/stake2 = implied1/implied2 (inverse of implied probs)

    Args:
        odds1: American odds for side 1
        odds2: American odds for side 2
        bankroll: Total dollar amount to split across both bets

    Returns a dict with:
        stake1 — Dollar amount to wager on side 1
        stake2 — Dollar amount to wager on side 2
    """
    try:
        implied1 = american_to_implied(odds1)
        implied2 = american_to_implied(odds2)

        if implied1 == 0.0 or implied2 == 0.0:
            return {"stake1": 0.0, "stake2": 0.0}

        # Weights are proportional to each side's implied probability
        # (the more likely side gets the smaller stake)
        stake1 = (implied1 / (implied1 + implied2)) * bankroll
        stake2 = (implied2 / (implied1 + implied2)) * bankroll

        return {
            "stake1": round(stake1, 2),
            "stake2": round(stake2, 2),
        }
    except Exception as e:
        print(f"[arb_calculator] Error in calculate_stakes: {e}")
        return {"stake1": 0.0, "stake2": 0.0}


def calculate_guaranteed_profit(odds1: int, odds2: int, bankroll: float) -> float:
    """
    Calculate the guaranteed dollar profit from an arbitrage opportunity.

    Uses the equal-profit stakes from calculate_stakes() and computes
    the net return on the winning side minus the full bankroll wagered.

    Args:
        odds1: American odds for side 1
        odds2: American odds for side 2
        bankroll: Total dollar amount to wager

    Returns:
        Guaranteed profit in dollars (float), or 0.0 if no arb.
    """
    try:
        arb = check_arb(odds1, odds2)
        if not arb["arb_exists"]:
            return 0.0

        stakes = calculate_stakes(odds1, odds2, bankroll)
        stake1 = stakes["stake1"]

        odds1 = int(odds1)
        # Calculate payout when side 1 wins
        if odds1 < 0:
            payout = stake1 + stake1 * (100 / abs(odds1))
        else:
            payout = stake1 + stake1 * (odds1 / 100)

        profit = payout - bankroll
        return round(profit, 2)
    except Exception as e:
        print(f"[arb_calculator] Error in calculate_guaranteed_profit: {e}")
        return 0.0


# ── Self-test when run directly ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("ARB CALCULATOR — SELF-TEST")
    print("=" * 60)

    test_cases = [
        {"odds1": -111, "odds2": 130,  "label": "Should find arb (~3.9%)"},
        {"odds1": -113, "odds2": -115, "label": "Should NOT find arb"},
        {"odds1": 105,  "odds2": 108,  "label": "Should find arb"},
    ]

    for tc in test_cases:
        o1, o2 = tc["odds1"], tc["odds2"]
        print(f"\nTest: {o1} vs +{o2} — {tc['label']}" if o2 > 0
              else f"\nTest: {o1} vs {o2} — {tc['label']}")

        result  = check_arb(o1, o2)
        stakes  = calculate_stakes(o1, o2, config.BANKROLL)
        profit  = calculate_guaranteed_profit(o1, o2, config.BANKROLL)

        print(f"  Implied 1 : {american_to_implied(o1):.4f}")
        print(f"  Implied 2 : {american_to_implied(o2):.4f}")
        print(f"  Total imp : {result['total_implied']:.4f}")
        print(f"  Profit %  : {result['profit_pct'] * 100:.2f}%")
        print(f"  Arb found : {result['arb_exists']}")
        if result["arb_exists"]:
            print(f"  Stake 1   : ${stakes['stake1']:.2f}")
            print(f"  Stake 2   : ${stakes['stake2']:.2f}")
            print(f"  Guaranteed profit: ${profit:.2f}")

    print("\n" + "=" * 60)
    print("Self-test complete.")
