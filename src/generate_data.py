from __future__ import annotations

from pathlib import Path
import random
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SEED = 20260910

CATEGORIES = {
    "Beverages": ["Purified Water 1L", "Cola 330ml", "Orange Drink 330ml", "Energy Drink 250ml", "Instant Coffee Mix", "Green Tea Bottle"],
    "Snacks": ["Potato Chips Small", "Cream Biscuit", "Wafer Roll", "Peanut Pack", "Seaweed Snack", "Cup Jelly"],
    "Staples": ["Rice 1 viss", "Cooking Oil 1L", "Sugar 500g", "Salt 400g", "Instant Noodles", "Fish Sauce 700ml"],
    "Household": ["Dishwashing Liquid", "Laundry Powder 500g", "Tissue Roll", "Garbage Bag Pack", "Sponge Pack", "Mosquito Coil"],
    "Personal Care": ["Bath Soap", "Shampoo Sachet Pack", "Toothpaste 100g", "Toothbrush", "Sanitary Pad Pack", "Baby Powder"],
    "Kitchen": ["Food Container", "Plastic Cup Pack", "Aluminium Foil", "Cling Film", "Scrub Brush"],
    "Stationery": ["Ball Pen", "Exercise Book", "Pencil Pack", "Eraser", "A4 Paper Pack"]
}

SUPPLIERS = [
    ("S01", "Shwe Pyi Distribution", "Hlaing", 2, 100000),
    ("S02", "Ayeyar Wholesale", "Bayint Naung", 3, 150000),
    ("S03", "Mingalar Consumer Supply", "Tamwe", 2, 80000),
    ("S04", "Thazin Household Trading", "Thingangyun", 4, 120000),
    ("S05", "Yadanar General Supply", "Insein", 5, 200000),
    ("S06", "Golden Land Essentials", "South Okkalapa", 3, 100000),
]

def round_price(value: float) -> int:
    return max(50, int(round(value / 50) * 50))

def make_products() -> pd.DataFrame:
    rng = random.Random(SEED)
    rows = []
    pid = 1
    for category, names in CATEGORIES.items():
        for name in names:
            cost = round_price(rng.uniform(180, 9000))
            margin = rng.uniform(0.10, 0.32)
            selling = round_price(cost / (1 - margin))
            supplier = SUPPLIERS[(pid - 1) % len(SUPPLIERS)][0]
            unit = "pack" if any(x in name.lower() for x in ["pack", "sachet", "paper"]) else "piece"
            rows.append((f"P{pid:03d}", name, category, unit, cost, selling, supplier, rng.randint(5, 18), True))
            pid += 1
    return pd.DataFrame(rows[:40], columns=["product_id","product_name","category","unit","default_purchase_price","default_selling_price","supplier_id","reorder_level","active"])

def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)
    np.random.seed(SEED)
    products = make_products()
    suppliers = pd.DataFrame(SUPPLIERS, columns=["supplier_id","supplier_name","township","lead_time_days","minimum_order_mmk"])
    products.to_csv(RAW / "products.csv", index=False)
    suppliers.to_csv(RAW / "suppliers.csv", index=False)

    start = pd.Timestamp("2026-06-01")
    dates = pd.date_range(start, periods=90, freq="D")
    popularity = np.random.lognormal(mean=0.3, sigma=0.7, size=len(products))
    popularity = popularity / popularity.sum()
    sales_rows, purchase_rows, count_rows = [], [], []
    sale_line, tx_no, purchase_line, purchase_no, count_no = 1, 1, 1, 1, 1

    for date in dates:
        weekday_factor = 1.18 if date.dayofweek >= 5 else 1.0
        baskets = np.random.poisson(33 * weekday_factor)
        for _ in range(baskets):
            transaction = f"T{tx_no:06d}"
            tx_no += 1
            line_count = np.random.choice([1,2,3], p=[0.63,0.28,0.09])
            choices = np.random.choice(products.index, size=line_count, replace=False, p=popularity)
            hour = int(np.clip(np.random.normal(14, 4), 7, 21))
            minute = random.randint(0, 59)
            for idx in choices:
                p = products.loc[idx]
                qty = int(np.random.choice([1,2,3,4], p=[0.72,0.20,0.06,0.02]))
                discount = 0 if random.random() > 0.08 else round_price(p.default_selling_price * qty * 0.05)
                payment = random.choices(["Cash","KBZPay","WavePay"], weights=[72,18,10])[0]
                sales_rows.append((f"SL{sale_line:07d}", transaction, date.replace(hour=hour, minute=minute), p.product_id, qty, p.default_selling_price, p.default_purchase_price, discount, payment))
                sale_line += 1

        if (date - start).days % 5 == 0:
            for supplier_id in suppliers.supplier_id:
                supplied = products[products.supplier_id == supplier_id]
                selected = supplied.sample(n=max(2, len(supplied)//2), random_state=SEED + date.dayofyear)
                purchase_id = f"PO{purchase_no:05d}"
                purchase_no += 1
                for _, p in selected.iterrows():
                    qty = random.randint(12, 45)
                    changed_cost = round_price(p.default_purchase_price * random.uniform(0.97, 1.05))
                    purchase_rows.append((f"PL{purchase_line:06d}", purchase_id, date.date(), supplier_id, p.product_id, qty, changed_cost))
                    purchase_line += 1

        if (date - start).days % 15 == 0:
            for _, p in products.iterrows():
                count_rows.append((f"IC{count_no:06d}", date.date(), p.product_id, random.randint(p.reorder_level, p.reorder_level + 45)))
                count_no += 1

    sales = pd.DataFrame(sales_rows, columns=["sale_line_id","transaction_id","sale_datetime","product_id","quantity","unit_selling_price","unit_cost","discount_mmk","payment_method"])
    purchases = pd.DataFrame(purchase_rows, columns=["purchase_line_id","purchase_id","purchase_date","supplier_id","product_id","quantity","unit_purchase_price"])
    counts = pd.DataFrame(count_rows, columns=["count_id","count_date","product_id","counted_quantity"])

    # Deliberate errors simulate ordinary operational data-quality failures.
    sales.loc[5, "product_id"] = "P999"
    sales.loc[13, "quantity"] = -2
    sales.loc[21, "payment_method"] = "cash"
    sales.loc[34, "unit_selling_price"] = np.nan
    sales = pd.concat([sales, sales.iloc[[50]]], ignore_index=True)
    purchases.loc[3, "supplier_id"] = "S99"
    purchases.loc[8, "quantity"] = 0
    counts.loc[7, "counted_quantity"] = -1

    sales.to_csv(RAW / "sales.csv", index=False)
    purchases.to_csv(RAW / "purchases.csv", index=False)
    counts.to_csv(RAW / "inventory_counts.csv", index=False)
    print(f"Generated {len(products)} products, {len(sales)} sale lines, {len(purchases)} purchase lines, and {len(counts)} counts.")

if __name__ == "__main__":
    main()

