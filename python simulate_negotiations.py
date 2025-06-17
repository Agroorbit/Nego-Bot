import json
import random
import time
from datetime import datetime

PRODUCTS_FILE = 'products_firms.json'

def negotiation_logic(product_name, product_code, firm, category, variant_name, variant_info, qty, offers):
    accepted = random.choice([True, False])
    return {
        "accepted": accepted,
        "final_offer": offers[-1],
        "stages": len(offers),
    }

with open(PRODUCTS_FILE, 'r') as f:
    firms = json.load(f)

firm_names = list(firms.keys())

def random_product_selection():
    firm = random.choice(firm_names)
    categories = list(firms[firm]['categories'].keys())
    category = random.choice(categories)
    products = firms[firm]['categories'][category]
    product = random.choice(products)
    variant_names = list(product['variants'].keys())
    variant = random.choice(variant_names)
    variant_info = product['variants'][variant]
    return firm, category, product, variant, variant_info

def random_offers(base_price):
    return [random.randint(int(0.8 * base_price), int(1.1 * base_price)) for _ in range(random.randint(1, 3))]

accepted = 0
rejected = 0
total_stages = 0
num_simulations = 10000000000000   # 100k! Will work fine with this efficient code
start_time = time.time()

for i in range(num_simulations):
    firm, category, product, variant, variant_info = random_product_selection()
    qty = random.randint(1, 100)
    base_price = variant_info['list_price']
    offers = random_offers(base_price)
    result = negotiation_logic(
        product_name=product["product_name"],
        product_code=product["product_code"],
        firm=firm,
        category=category,
        variant_name=variant,
        variant_info=variant_info,
        qty=qty,
        offers=offers
    )
    if result["accepted"]:
        accepted += 1
    else:
        rejected += 1
    total_stages += result["stages"]
    if (i+1) % 10000 == 0:
        print(f"Simulated {i+1} negotiations...")

elapsed = time.time() - start_time
print(f"\n--- Stress Test Results ---")
print(f"Total Negotiations: {num_simulations}")
print(f"Time Taken: {elapsed:.2f} seconds")
print(f"Average per negotiation: {elapsed / num_simulations:.6f} seconds")
print(f"Accepted: {accepted} | Rejected: {rejected}")
print(f"Average stages per negotiation: {total_stages / num_simulations:.2f}")
