def main_negotiation_min(cp, lp):
    """
    Calculates the negotiation minimum using all 3 main rules:
    - At least 12% above cp
    - Or at least Rs 100 above cp
    - Never more than 82% of lp
    - Never below cp
    Returns the correct main minimum value as a float.
    """
    min_12pct = cp * 1.12
    min_100rs = cp + 100
    max_82pct_lp = lp * 0.82

    negotiation_min = max(min_12pct, min_100rs)
    negotiation_min = min(negotiation_min, max_82pct_lp)
    negotiation_min = max(negotiation_min, cp)
    return negotiation_min

def fallback_negotiation_min(cp, lp):
    """
    Calculates the fallback negotiation minimum:
    - cp + 60% of the gap (lp - cp)
    Returns the fallback minimum value as a float.
    """
    return cp + 0.6 * (lp - cp)
