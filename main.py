import json
import random
import os
from datetime import datetime

from negotiation_formulas import main_negotiation_min, fallback_negotiation_min
from negotiation_helpers import classify_product, fallback_counter_offer
from dynamic_margin import get_hybrid_min_negotiation, get_recent_order_count, get_dynamic_wiggle_room
from negotiation_event_logger import log_event

# ---------- CONFIGURATION ----------
PRODUCTS_FILE = r'D:\Bot\products_firms.json'
LOG_FILE = r'D:\New Bot\negotiation_cli_log.json'
EVENT_LOG_FILE = "negotiation_events.jsonl"
CONTACT_EMAIL = "sales@yourcompany.com"
CONTACT_PHONE = "+91-XXXXXXXXXX"
BULK_SUGGEST_TOLERANCE = 20
BULK_THRESHOLD_TOLERANCE = 5
ROLLING_WINDOW_DAYS = 30

def load_all_sessions():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    print("Log file was a dict. Resetting to empty list.")
                    return []
                elif isinstance(data, list):
                    return data
                else:
                    print("Log file not a list or dict. Resetting to empty list.")
                    return []
            except json.decoder.JSONDecodeError:
                print("Log file is empty or corrupt. Resetting to empty list.")
                return []
    else:
        return []

all_sessions = load_all_sessions()

with open(PRODUCTS_FILE, 'r') as f:
    firms = json.load(f)

def list_firms():
    print("\nAvailable Firms:")
    for idx, firm in enumerate(firms, 1):
        print(f"{idx}. {firm}")
    print()

def select_firm():
    list_firms()
    firm_input = input("Enter firm number or name: ").strip()
    firm_list = list(firms.keys())
    firm_name = None
    if firm_input.isdigit():
        firm_idx = int(firm_input) - 1
        if 0 <= firm_idx < len(firm_list):
            firm_name = firm_list[firm_idx]
    else:
        for fname in firm_list:
            if fname.lower() == firm_input.lower():
                firm_name = fname
                break
    if not firm_name:
        print("Firm not found."); return None
    return firm_name

def list_categories(firm_name):
    categories = firms[firm_name]['categories']
    print(f"\nCategories in '{firm_name}':")
    for idx, cat in enumerate(categories, 1):
        print(f"{idx}. {cat}")
    print()

def select_category(firm_name):
    categories = list(firms[firm_name]['categories'].keys())
    list_categories(firm_name)
    cat_input = input("Enter category number or name: ").strip()
    cat_name = None
    if cat_input.isdigit():
        cat_idx = int(cat_input) - 1
        if 0 <= cat_idx < len(categories):
            cat_name = categories[cat_idx]
    else:
        for cname in categories:
            if cname.lower() == cat_input.lower():
                cat_name = cname
                break
    if not cat_name:
        print("Category not found."); return None
    return cat_name

def list_products(firm_name, category):
    products = firms[firm_name]['categories'][category]
    print(f"\nProducts in '{firm_name}' > '{category}':")
    for idx, prod in enumerate(products, 1):
        print(f"{idx}. {prod['product_name']} | Code: {prod['product_code']}")
        print("   Variants:", ", ".join(prod['variants'].keys()))
    print()

def select_product(firm_name, category):
    products = firms[firm_name]['categories'][category]
    list_products(firm_name, category)
    prod_input = input("Enter product number or product code: ").strip()
    prod = None
    if prod_input.isdigit():
        prod_idx = int(prod_input) - 1
        if 0 <= prod_idx < len(products):
            prod = products[prod_idx]
    else:
        for p in products:
            if p['product_code'].lower() == prod_input.lower():
                prod = p
                break
    if not prod:
        print("Product not found."); return None
    return prod

def show_variant_details(prod):
    print("\nAvailable Variants:")
    variant_names = list(prod['variants'].keys())
    for idx, vname in enumerate(variant_names, 1):
        print(f"{idx}. {vname}")
    v_choice = input("Select variant by number or name: ").strip()
    vinfo = None
    vname_final = None
    if v_choice.isdigit():
        v_idx = int(v_choice) - 1
        if 0 <= v_idx < len(variant_names):
            vname_final = variant_names[v_idx]
            vinfo = prod['variants'][vname_final]
    else:
        for vname in variant_names:
            if vname.lower() == v_choice.lower():
                vname_final = vname
                vinfo = prod['variants'][vname]
                break
    if vinfo:
        print("\nVariant details:")
        for k, v in vinfo.items():
            print(f"  {k}: {v}")
        return vname_final, vinfo
    else:
        print("Variant not found."); return None, None

def negotiation_logic(product_name, product_code, firm, category, variant_name, variant_info, qty):
    lp = variant_info["list_price"]
    cp = variant_info["cost_price"]
    bp = variant_info["bulk_price"]
    bt = variant_info["bulk_threshold"]
    user_id = random.randint(1000, 9999)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    session_id = max((s.get("id", 0) for s in all_sessions), default=0) + 1

    order_count = get_recent_order_count(product_code, ROLLING_WINDOW_DAYS, EVENT_LOG_FILE)
    wiggle_room = get_dynamic_wiggle_room(lp, cp)

    min_negotiation, classification = get_hybrid_min_negotiation(
        cp, lp, order_count, bp, qty, bt, product_code, EVENT_LOG_FILE
    )

    session_log = {
        "id": session_id,
        "quantity": qty,
        "created_at": now,
        "updated_at": now,
        "product_code": product_code,
        "product_name": product_name,
        "variant": variant_name,
        "price": lp,
        "cost_price": cp,
        "firm": firm,
        "category": category,
        "negotiation_min": min_negotiation,
        "classification": classification,
        "history": [],
        "final_status": None,
        "final_price": None,
        "user_id": user_id,
        "contact_option": {"show": False, "message": ""}
    }

    print(f"\n🛒 Negotiation for {product_name} ({variant_name})")
    print(f"Firm: {firm}")
    print(f"Category: {category}")
    print(f"List Price: ₹{lp}")
    print(f"Bulk Price: ₹{bp}")
    print(f"Bulk Threshold: {bt}")
    print(f"Margin classification: {classification}")

    # --- Bulk threshold nudge before negotiation loop ---
    if qty < bt and (bt - qty) <= BULK_THRESHOLD_TOLERANCE:
        print(f"\n💡 You’re only {bt - qty} unit(s) away from unlocking the bulk price of ₹{bp} per unit!")
        upgrade = input(f"Would you like to increase your quantity to {bt} and get the better rate? (yes/no): ").strip().lower()
        if upgrade == "yes":
            qty = bt
            print(f"\n👍 Quantity upgraded to {bt} units. Let's negotiate at the bulk rate!")
            min_negotiation, classification = get_hybrid_min_negotiation(
                cp, lp, order_count, bp, qty, bt, product_code, EVENT_LOG_FILE
            )
        else:
            print(f"\nOkay, proceeding with your original quantity of {qty} units.")

    if classification == "no_negotiation" or min_negotiation is None:
        print(f"\n❌ Negotiation is not possible for this product due to tight pricing (margin too thin for any wiggle room).")
        session_log["final_status"] = "no deal"
        session_log["final_price"] = None
        session_log["contact_option"] = {
            "show": True,
            "message": f"Contact our sales professional at {CONTACT_EMAIL} or {CONTACT_PHONE} for assistance."
        }
        all_sessions.append(session_log)
        with open(LOG_FILE, "w") as f:
            json.dump(all_sessions, f, indent=4)
        log_event("negotiation_blocked", {
            "product_code": product_code,
            "qty": qty,
            "lp": lp,
            "cp": cp,
            "classification": classification,
            "order_count": order_count,
            "reason": "Margin below wiggle room"
        })
        return

    accepted = False
    history = []
    stage, last_ctr = 0, None

    if classification == "main":
        while not accepted and stage < 3:
            try:
                offer = int(input("\n💬 Your offer per unit (₹): "))
            except Exception:
                print("\n❌ Invalid offer input.")
                continue

            # Bulk price suggestion if offer close to bulk price
            if qty < bt and abs(offer - bp) <= BULK_SUGGEST_TOLERANCE:
                print(f"\n💡 If you increase your quantity to {bt}, you can get the bulk price of ₹{bp} per unit.")
                upgrade = input(f"Would you like to proceed with a bulk order of {bt} units? (yes/no): ").strip().lower()
                if upgrade == "yes":
                    qty = bt
                    print(f"\n👍 Quantity upgraded to {bt} units. Let's negotiate at the bulk rate!")
                    min_negotiation, classification = get_hybrid_min_negotiation(
                        cp, lp, order_count, bp, qty, bt, product_code, EVENT_LOG_FILE
                    )
                    continue
                else:
                    print(f"\nOkay, proceeding with your original quantity of {qty} units.")

            if offer < min_negotiation:
                resp = f'🛑 Sorry, we can\'t go below ₹{min_negotiation}.'
                print(f"\n🤖 {resp}")
                session_log["history"].append({
                    "round": stage + 1,
                    "user_offer": offer,
                    "bot_reply": resp,
                    "bot_counter_offer": min_negotiation,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                })
                session_log["final_status"] = "no deal"
                session_log["final_price"] = None
                session_log["contact_option"] = {
                    "show": True,
                    "message": f"Contact our sales professional at {CONTACT_EMAIL} or {CONTACT_PHONE} for assistance."
                }
                break

            if last_ctr is not None and offer >= last_ctr and offer >= min_negotiation:
                resp, status, accepted = f"✅ Great! We'll proceed at ₹{offer}!", "accepted", True
            elif offer >= lp or (lp - offer <= 5 and qty < bt) and offer >= min_negotiation:
                resp, status, accepted = f"✅ Accepted at ₹{offer}!", "accepted", True
            elif qty >= bt and offer >= bp and offer >= min_negotiation:
                resp, status, accepted = f"📦 Bulk deal: ₹{offer} for {qty} units.", "accepted", True
            elif ((stage == 0 and lp - offer <= 5)
                  or (stage == 1 and lp - offer <= 7)
                  or (stage == 2 and lp - offer <= 10)) and offer >= min_negotiation:
                resp, status, accepted = f"✅ Accepted at ₹{offer}!", "accepted", True
            else:
                if offer in history:
                    print(f"\n🤖 🔁 You already offered ₹{offer}.")
                    continue
                if history and offer < max(history):
                    print(f"\n🤖 🔻 That's below your previous best of ₹{max(history)}.")
                    continue
                stage += 1
                if stage == 1:
                    last_ctr = min(lp, offer + 30)
                elif stage == 2:
                    last_ctr = (last_ctr + offer) // 2
                else:
                    avg = (offer + cp) // 2
                    last_ctr = max(offer, avg)
                last_ctr = max(last_ctr, min_negotiation)
                if last_ctr == offer and offer >= min_negotiation:
                    resp, status, accepted = f"✅ Great! We'll proceed at ₹{offer}!", "accepted", True
                else:
                    resp, status = f"🤝 We'd be comfortable at ₹{last_ctr}.", "pending"

            history.append(offer)
            session_log["history"].append({
                "round": stage,
                "user_offer": offer,
                "bot_reply": resp,
                "bot_counter_offer": last_ctr if last_ctr is not None else None,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            })
            print(f"\n🤖 {resp}")

    else:
        # Fallback logic for non-main
        fallback_min = fallback_negotiation_min(cp, lp)
        session_log["negotiation_min"] = fallback_min
        accepted = False
        round_num = 1
        last_bot_offer = None

        print(f"\n🤖 This product is special—let's negotiate!")
        while round_num <= 2 and not accepted:
            try:
                offer = int(input(f"\n💬 Your offer per unit (₹): "))
            except Exception:
                print("\n❌ Invalid offer input.")
                continue

            if offer >= fallback_min and offer <= lp:
                resp = f"✅ Great! We'll proceed at ₹{offer}!"
                session_log["history"].append({
                    "round": round_num,
                    "user_offer": offer,
                    "bot_reply": resp,
                    "bot_counter_offer": offer,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                })
                print(f"\n🤖 {resp}")
                session_log["final_status"] = "deal"
                session_log["final_price"] = offer
                log_event("deal_closed", {
                    "product_code": product_code,
                    "qty": qty,
                    "lp": lp,
                    "cp": cp,
                    "negotiation_min": fallback_min,
                    "classification": "fallback",
                    "order_count": order_count
                })
                log_event("order_summary", {
                    "order_id": session_id,
                    "product_code": product_code,
                    "quantity": qty,
                    "timestamp": datetime.now().isoformat()
                })
                accepted = True
                break

            bot_counter = fallback_counter_offer(offer, fallback_min, lp, round_num)
            if last_bot_offer and bot_counter > last_bot_offer:
                bot_counter = last_bot_offer
            last_bot_offer = bot_counter

            if round_num == 1:
                resp = f"🤝 I can't go that low, but I can do ₹{bot_counter}."
            else:
                resp = f"🤝 That's the lowest possible price: ₹{bot_counter}."

            session_log["history"].append({
                "round": round_num,
                "user_offer": offer,
                "bot_reply": resp,
                "bot_counter_offer": bot_counter,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            })
            print(f"\n🤖 {resp}")
            round_num += 1

        if not accepted:
            print("\n🤝 We couldn't finalize the deal. Would you like to contact a professional for assistance?")
            print(f"Contact: {CONTACT_EMAIL} or call {CONTACT_PHONE}")
            session_log["final_status"] = "no deal"
            session_log["final_price"] = None
            session_log["contact_option"] = {
                "show": True,
                "message": f"Contact our sales professional at {CONTACT_EMAIL} or {CONTACT_PHONE} for assistance."
            }

    session_log["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    all_sessions.append(session_log)
    with open(LOG_FILE, "w") as f:
        json.dump(all_sessions, f, indent=4)
    print("\n✅ Negotiation complete. Log → negotiation_cli_log.json")

def main_flow():
    firm_name = select_firm()
    if not firm_name:
        return
    cat_name = select_category(firm_name)
    if not cat_name:
        return
    prod = select_product(firm_name, cat_name)
    if not prod:
        return
    vname, vinfo = show_variant_details(prod)
    if not vname:
        return
    try:
        qty = int(input("\nEnter quantity you want to purchase: "))
        if qty <= 0:
            print("Quantity must be greater than 0.")
            return
    except Exception:
        print("Invalid quantity.")
        return
    negotiation_logic(
        product_name=prod["product_name"],
        product_code=prod["product_code"],
        firm=firm_name,
        category=cat_name,
        variant_name=vname,
        variant_info=vinfo,
        qty=qty
    )

if __name__ == "__main__":
    main_flow()
