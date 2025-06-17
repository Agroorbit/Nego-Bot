import json
import random
import os
from datetime import datetime

# ---------- CONFIGURATION ----------
PRODUCTS_FILE = r'D:\Bot\products_firms.json'  # Update path if needed
LOG_FILE = r'D:\New Bot\negotiation_cli_log.json'
CONTACT_EMAIL = "sales@yourcompany.com"
CONTACT_PHONE = "+91-XXXXXXXXXX"
BULK_SUGGEST_TOLERANCE = 20

# ---------- LOG LOADING ----------
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

# ---------- LOAD PRODUCT DATA ----------
with open(PRODUCTS_FILE, 'r') as f:
    firms = json.load(f)

# ---------- SELECTION FUNCTIONS ----------
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

# ---------- NEGOTIATION LOGIC ----------
def get_negotiation_min(qty, cp, lp, bp, bt):
    if qty >= bt:
        min_percent = int(cp * 1.08)
        min_absolute = cp + 70
        negotiation_min = max(min_percent, min_absolute)
        min_bulk_allowed = int(bp * 0.98)
        negotiation_min = max(negotiation_min, min_bulk_allowed)
    else:
        min_percent = int(cp * 1.12)
        min_absolute = cp + 100
        negotiation_min = max(min_percent, min_absolute)
        max_allowed = int(lp * 0.82)
        negotiation_min = min(negotiation_min, max_allowed)
    negotiation_min = max(negotiation_min, cp)
    return negotiation_min

def negotiation_logic(product_name, product_code, firm, category, variant_name, variant_info, qty):
    lp = variant_info["list_price"]
    cp = variant_info["cost_price"]
    bp = variant_info["bulk_price"]
    bt = variant_info["bulk_threshold"]
    negotiation_min = get_negotiation_min(qty, cp, lp, bp, bt)

    # ----- Show details (one per line, no cost price, no negotiation min) -----
    print(f"\n🛒 Negotiation for {product_name} ({variant_name})")
    print(f"Firm: {firm}")
    print(f"Category: {category}")
    print(f"List Price: ₹{lp}")
    print(f"Bulk Price: ₹{bp}")
    print(f"Bulk Threshold: {bt}")

    log, history = [], []
    stage, last_ctr = 0, None
    accepted = False
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    user_id = random.randint(1000, 9999)
    contact_needed = False

    while not accepted and stage < 3:
        try:
            offer = int(input("\n💬 Your offer per unit (₹): "))
        except Exception:
            print("\n❌ Invalid offer input."); continue

        # Suggest Bulk Upgrade
        if qty < bt and abs(offer - bp) <= BULK_SUGGEST_TOLERANCE:
            print(f"\n💡 If you increase your quantity to {bt}, you can get the bulk price of ₹{bp} per unit.")
            upgrade = input(f"Would you like to proceed with a bulk order of {bt} units? (yes/no): ").strip().lower()
            if upgrade == "yes":
                qty = bt
                print(f"\n👍 Quantity upgraded to {bt} units. Let's negotiate at the bulk rate!")
                negotiation_min = get_negotiation_min(qty, cp, lp, bp, bt)
                continue
            else:
                print(f"\nOkay, proceeding with your original quantity of {qty} units.")

        if offer < negotiation_min:
            resp = f'🛑 Sorry, we can\'t go below ₹{negotiation_min}.'
            log.append({"user_offer": offer, "bot_reply": resp, "stage": stage, "status": "rejected"})
            print(f"\n🤖 {resp}")
            contact_needed = True
            break

        if last_ctr is not None and offer >= last_ctr and offer >= negotiation_min:
            resp, status, accepted = f"✅ Great! We'll proceed at ₹{offer}!", "accepted", True
        elif offer >= lp or (lp - offer <= 5 and qty < bt) and offer >= negotiation_min:
            resp, status, accepted = f"✅ Accepted at ₹{offer}!", "accepted", True
        elif qty >= bt and offer >= bp and offer >= negotiation_min:
            resp, status, accepted = f"📦 Bulk deal: ₹{offer} for {qty} units.", "accepted", True
        elif ((stage == 0 and lp - offer <= 5)
              or (stage == 1 and lp - offer <= 7)
              or (stage == 2 and lp - offer <= 10)) and offer >= negotiation_min:
            resp, status, accepted = f"✅ Accepted at ₹{offer}!", "accepted", True
        else:
            if offer in history:
                print(f"\n🤖 🔁 You already offered ₹{offer}."); continue
            if history and offer < max(history):
                print(f"\n🤖 🔻 That's below your previous best of ₹{max(history)}."); continue
            stage += 1
            if stage == 1:
                last_ctr = min(lp, offer + 30)
            elif stage == 2:
                last_ctr = (last_ctr + offer) // 2
            else:
                avg = (offer + cp) // 2
                last_ctr = max(offer, avg)
            last_ctr = max(last_ctr, negotiation_min)
            if last_ctr == offer and offer >= negotiation_min:
                resp, status, accepted = f"✅ Great! We'll proceed at ₹{offer}!", "accepted", True
            else:
                resp, status = f"🤝 We'd be comfortable at ₹{last_ctr}.", "pending"

        history.append(offer)
        log.append({"user_offer": offer, "bot_reply": resp, "stage": stage, "status": status if accepted else "pending"})
        print(f"\n🤖 {resp}")

    if not accepted:
        contact_needed = True
        print("\n🤝 We couldn't finalize the deal. Would you like to contact a professional for assistance?")
        print(f"Contact: {CONTACT_EMAIL} or call {CONTACT_PHONE}")

    session_id = max((s.get("id", 0) for s in all_sessions), default=0) + 1
    session = {
        "id": session_id,
        "quantity": qty,
        "created_at": now,
        "updated_at": now,
        "product_code": product_code,
        "product_name": product_name,
        "variant": variant_name,
        "price": lp,
        "cost_price": cp,  # <-- add this line
        "status": log[-1]["status"] if log else "no deal",
        "user_id": user_id,
        "history": log,
        "contact_option": {
            "show": contact_needed,
            "message": (
                f"Contact our sales professional at {CONTACT_EMAIL} or {CONTACT_PHONE} for assistance."
                if contact_needed else ""
            )
        },
        "min_negotiable_price": negotiation_min
                }

    
    all_sessions.append(session)
    with open(LOG_FILE, "w") as f:
        json.dump(all_sessions, f, indent=4)

    print("\n✅ Negotiation complete. Log → negotiation_cli_log.json")

# ---------- MAIN FLOW ----------
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
