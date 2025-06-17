import numpy as np
import os
import json
from datetime import datetime, timedelta

# --- CONFIGURABLE SETTINGS ---
ROLLING_WINDOW_DAYS = 30
WIGGLE_MIN_PCT = 0.05
WIGGLE_MIN_RS = 20
WIGGLE_MIN_WIGGLE = 2  # Minimum possible wiggle for low-value items
WIGGLE_MAX_MARGIN_PCT = 0.5  # Never allow wiggle room > 50% of (lp-cp)
PLATEAU_MARGIN = 20.0
PLATEAU_DURATION = 15  # days
ACTIVITY_THRESHOLD = 25
DECLINE_RATE = 2  # percent per step
DECLINE_STEP_DAYS = 3

# --- 1. Sigmoid Margin Function with Threshold ---
def sigmoid_margin(order_count, max_margin=20, k=0.01, midpoint=750, threshold=50):
    if order_count < threshold:
        return 0
    return max_margin / (1 + np.exp(-k * (order_count - midpoint)))

# --- 2. Plateau/Decline State From Log ---
def get_plateau_state_from_log(product_code, event_log_file, plateau_margin=PLATEAU_MARGIN):
    plateau_start_date = None
    decline_start_date = None
    in_decline = False
    plateau_sales_since = 0

    events = []
    if not os.path.exists(event_log_file):
        return {
            "plateau_start_date": None,
            "plateau_sales_since": 0,
            "in_decline": False,
            "decline_start_date": None,
        }

    with open(event_log_file, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("product_code") == product_code:
                    events.append(entry)
            except Exception:
                continue

    events = sorted(events, key=lambda x: x["timestamp"], reverse=True)

    # Find last time margin reached plateau (20%)
    for entry in events:
        margin = entry.get("margin_pct", None)
        if margin is not None and float(margin) >= (plateau_margin - 0.01):
            plateau_start_date = datetime.fromisoformat(entry["timestamp"])
            break

    if plateau_start_date is None:
        return {
            "plateau_start_date": None,
            "plateau_sales_since": 0,
            "in_decline": False,
            "decline_start_date": None,
        }

    # Count units sold since plateau
    plateau_sales_since = 0
    for entry in events:
        entry_time = datetime.fromisoformat(entry["timestamp"])
        if entry_time >= plateau_start_date:
            if entry.get("event") in ("deal_closed", "order_summary"):
                qty = int(entry.get("quantity", 1))
                plateau_sales_since += qty

    now = datetime.now()
    days_on_plateau = (now - plateau_start_date).days
    if days_on_plateau > PLATEAU_DURATION and plateau_sales_since < ACTIVITY_THRESHOLD:
        in_decline = True
        decline_start_date = plateau_start_date + timedelta(days=PLATEAU_DURATION)

    return {
        "plateau_start_date": plateau_start_date,
        "plateau_sales_since": plateau_sales_since,
        "in_decline": in_decline,
        "decline_start_date": decline_start_date,
    }

# --- 3. Dynamic Margin Calculation with Plateau/Decline via Event Log ---
def get_dynamic_margin_with_log(product_code, order_count, event_log_file):
    state = get_plateau_state_from_log(product_code, event_log_file)
    now = datetime.now()

    if state["plateau_start_date"] is None:
        # Never hit plateau
        return sigmoid_margin(order_count)

    # On plateau, not yet in decline
    days_on_plateau = (now - state["plateau_start_date"]).days
    if not state["in_decline"]:
        if days_on_plateau < PLATEAU_DURATION:
            if state["plateau_sales_since"] >= ACTIVITY_THRESHOLD:
                # Activity resets plateau
                return PLATEAU_MARGIN
            else:
                return PLATEAU_MARGIN
        else:
            # Plateau expired, start decline
            days_since_decline = (now - (state["plateau_start_date"] + timedelta(days=PLATEAU_DURATION))).days
    else:
        days_since_decline = (now - state["decline_start_date"]).days

    # In decline: stepwise down, but never below sigmoid
    decline_steps = days_since_decline // DECLINE_STEP_DAYS
    declined_margin = PLATEAU_MARGIN - DECLINE_RATE * decline_steps
    floor_margin = sigmoid_margin(order_count)
    return max(declined_margin, floor_margin)

# --- 4. Dynamic Margin Cap Calculation ---
def calculate_margin_cap(cost_price, bulk_price, buffer=1.0):
    if bulk_price <= 0 or bulk_price <= cost_price:
        return 0
    gross_margin = (bulk_price - cost_price) * buffer
    return 100 * gross_margin / bulk_price

# --- 5. Dynamic Wiggle Room (NEW & IMPROVED, Option 1) ---
def get_dynamic_wiggle_room(
    lp,
    cp,
    min_percent=WIGGLE_MIN_PCT,
    min_room=WIGGLE_MIN_RS,
    min_wiggle=WIGGLE_MIN_WIGGLE,
    max_pct_of_margin=WIGGLE_MAX_MARGIN_PCT
):
    available_margin = max(lp - cp, min_wiggle)
    calculated_wiggle = max(lp * min_percent, min_room, min_wiggle)
    safe_cap = available_margin * max_pct_of_margin
    return min(calculated_wiggle, available_margin, safe_cap)

# --- 6. Product Classification (No Negotiation, Fallback, Main) ---
def classify_product(cp, lp, wiggle_room):
    threshold = min(cp * 0.12, 100)
    margin = lp - cp
    if margin < wiggle_room:
        return "no_negotiation"
    elif margin <= threshold:
        return "fallback"
    else:
        return "main"

# --- 7. Main (Classic) Negotiation Minimum ---
def classic_min_negotiation(cp, lp):
    min_12pct = cp * 1.12
    min_100rs = cp + 100
    max_82pct_lp = lp * 0.82
    negotiation_min = max(min_12pct, min_100rs)
    negotiation_min = min(negotiation_min, max_82pct_lp)
    negotiation_min = max(negotiation_min, cp)
    return negotiation_min

# --- 8. Bulk Margin Cap for Fallback ---
def get_min_bulk_margin(cp, percent=0.06, min_rs=20, max_rs=200):
    margin = cp * percent
    return min(max(margin, min_rs), max_rs)

# --- 9. Hybrid Margin Calculation (with Plateau/Decline Logic via Event Log) ---
def get_hybrid_min_negotiation(
    cp, lp, order_count, bulk_price, qty, bulk_threshold, product_code, event_log_file, buffer=1.0, min_margin_buffer=2
):
    """
    Returns the minimum negotiation price and formula used (hybrid logic) using event log for margin logic.
    """
    wiggle_room = get_dynamic_wiggle_room(lp, cp)
    classification = classify_product(cp, lp, wiggle_room)
    cap = calculate_margin_cap(cp, bulk_price, buffer)

    # Use event log for dynamic margin plateau/decline logic
    sig_margin = get_dynamic_margin_with_log(product_code, order_count, event_log_file)
    dynamic_margin = min(sig_margin, cap)
    classic_min = classic_min_negotiation(cp, lp)
    sigmoid_min = classic_min + dynamic_margin

    # Fallback logic (bulk or not)
    is_bulk = qty >= bulk_threshold
    if is_bulk:
        fallback_min = max(bulk_price, cp + get_min_bulk_margin(cp))
    else:
        fallback_min = cp + 0.6 * (lp - cp)

    hard_min = cp + min_margin_buffer
    candidate_min = max(classic_min, sigmoid_min, hard_min)
    if classification == "fallback":
        candidate_min = max(fallback_min, hard_min)
    if classification == "no_negotiation":
        return None, "no_negotiation"
    final_min = min(candidate_min, lp - wiggle_room)
    return final_min, classification

# --- 10. Get Rolling Order Count for Product ---
def get_recent_order_count(product_code, days, log_file):
    if not os.path.exists(log_file):
        return 0
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    total_qty = 0
    with open(log_file, 'r') as f:
        for line in f:
            record = json.loads(line)
            if (
                record.get('event') == 'order_summary'
                and record.get('product_code') == product_code
                and 'quantity' in record
            ):
                order_time = datetime.fromisoformat(record['timestamp'])
                if order_time >= cutoff:
                    total_qty += int(record['quantity'])
    return total_qty

# --- Example Usage for Testing ---
if __name__ == "__main__":
    cp = 90
    lp = 100
    bulk_price = 95
    qty = 10
    bulk_threshold = 50
    order_count = 1050
    product_code = "PROD1"
    event_log_file = "negotiation_events.jsonl"  # Make sure this exists for real tests!

    min_neg, classification = get_hybrid_min_negotiation(
        cp, lp, order_count, bulk_price, qty, bulk_threshold, product_code, event_log_file
    )
    print(f"Negotiation min: {min_neg} | Classification: {classification}")
