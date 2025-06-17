# negotiation_helpers.py

def classify_product(cp, lp, wiggle_room=None):
    """
    Classifies product for negotiation formula.
    Returns:
        - 'main' if (lp-cp) > threshold,
        - 'fallback' if margin is thin but above wiggle_room,
        - 'no_negotiation' if (lp-cp) < wiggle_room.
    Threshold: min(12% of cost price, Rs 100).
    """
    threshold = min(cp * 0.12, 100)
    margin = lp - cp
    if wiggle_room is not None and margin < wiggle_room:
        return 'no_negotiation'
    return 'main' if margin > threshold else 'fallback'

def fallback_counter_offer(customer_offer, fallback_min, lp, round_num, offset_pct=0.1):
    """
    Bot's counter offer logic for fallback negotiation.
    - First round: fallback_min + 10% of gap (min Rs 5), never above lp.
    - Second (or later) round: fallback_min (the floor).
    """
    if round_num == 1:
        dynamic_offset = max(int(abs(customer_offer - fallback_min) * offset_pct), 5)
        return min(fallback_min + dynamic_offset, lp)
    else:
        return fallback_min

# negotiation_formulas.py

def main_negotiation_min(cp, lp):
    """
    Main negotiation minimum:
    - At least 12% above cp,
    - Or at least Rs 100 above cp,
    - Never more than 82% of lp,
    - Never below cp.
    Returns a float.
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
    Fallback negotiation minimum:
    - cp + 60% of (lp - cp)
    Returns a float.
    """
    return cp + 0.6 * (lp - cp)
