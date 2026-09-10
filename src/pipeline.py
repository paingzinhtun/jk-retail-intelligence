from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

def reject(df: pd.DataFrame, mask: pd.Series, reason: str, rejected: list[pd.DataFrame]) -> pd.DataFrame:
    if mask.any():
        bad = df.loc[mask].copy()
        bad["rejection_reason"] = reason
        rejected.append(bad)
    return df.loc[~mask].copy()

def validate_sales(sales: pd.DataFrame, product_ids: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rejected: list[pd.DataFrame] = []
    sales["sale_datetime"] = pd.to_datetime(sales["sale_datetime"], errors="coerce")
    for col in ["quantity","unit_selling_price","unit_cost","discount_mmk"]:
        sales[col] = pd.to_numeric(sales[col], errors="coerce")
    sales = reject(sales, sales.sale_line_id.duplicated(keep="first"), "duplicate_sale_line_id", rejected)
    sales = reject(sales, ~sales.product_id.isin(product_ids), "unknown_product_id", rejected)
    sales = reject(sales, sales.sale_datetime.isna(), "invalid_sale_datetime", rejected)
    sales = reject(sales, sales.quantity.isna() | (sales.quantity <= 0), "quantity_not_positive", rejected)
    sales = reject(sales, sales.unit_selling_price.isna() | (sales.unit_selling_price <= 0), "invalid_selling_price", rejected)
    sales = reject(sales, sales.unit_cost.isna() | (sales.unit_cost <= 0), "invalid_unit_cost", rejected)
    sales = reject(sales, ~sales.payment_method.isin(["Cash","KBZPay","WavePay"]), "invalid_payment_method", rejected)
    invalid_discount = (sales.discount_mmk < 0) | (sales.discount_mmk >= sales.quantity * sales.unit_selling_price)
    sales = reject(sales, invalid_discount, "invalid_discount", rejected)
    sales["quantity"] = sales.quantity.astype(int)
    for col in ["unit_selling_price","unit_cost","discount_mmk"]:
        sales[col] = sales[col].astype(int)
    sales["revenue_mmk"] = sales.quantity * sales.unit_selling_price - sales.discount_mmk
    sales["estimated_cogs_mmk"] = sales.quantity * sales.unit_cost
    sales["gross_profit_mmk"] = sales.revenue_mmk - sales.estimated_cogs_mmk
    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    return sales, rejected_df

def validate_purchases(df: pd.DataFrame, product_ids: set[str], supplier_ids: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rejected: list[pd.DataFrame] = []
    df["purchase_date"] = pd.to_datetime(df.purchase_date, errors="coerce")
    for col in ["quantity","unit_purchase_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = reject(df, df.purchase_line_id.duplicated(keep="first"), "duplicate_purchase_line_id", rejected)
    df = reject(df, ~df.product_id.isin(product_ids), "unknown_product_id", rejected)
    df = reject(df, ~df.supplier_id.isin(supplier_ids), "unknown_supplier_id", rejected)
    df = reject(df, df.purchase_date.isna(), "invalid_purchase_date", rejected)
    df = reject(df, df.quantity.isna() | (df.quantity <= 0), "quantity_not_positive", rejected)
    df = reject(df, df.unit_purchase_price.isna() | (df.unit_purchase_price <= 0), "invalid_purchase_price", rejected)
    df["quantity"] = df.quantity.astype(int)
    df["unit_purchase_price"] = df.unit_purchase_price.astype(int)
    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    return df, rejected_df

def validate_counts(df: pd.DataFrame, product_ids: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rejected: list[pd.DataFrame] = []
    df["count_date"] = pd.to_datetime(df.count_date, errors="coerce")
    df["counted_quantity"] = pd.to_numeric(df.counted_quantity, errors="coerce")
    df = reject(df, df.count_id.duplicated(keep="first"), "duplicate_count_id", rejected)
    df = reject(df, ~df.product_id.isin(product_ids), "unknown_product_id", rejected)
    df = reject(df, df.count_date.isna(), "invalid_count_date", rejected)
    df = reject(df, df.counted_quantity.isna() | (df.counted_quantity < 0), "negative_or_missing_count", rejected)
    df["counted_quantity"] = df.counted_quantity.astype(int)
    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    return df, rejected_df

def build_outputs(products: pd.DataFrame, suppliers: pd.DataFrame, sales: pd.DataFrame, purchases: pd.DataFrame, counts: pd.DataFrame) -> dict:
    max_date = sales.sale_datetime.max().normalize()
    window_start = max_date - pd.Timedelta(days=29)
    recent = sales[sales.sale_datetime >= window_start]
    perf = recent.groupby("product_id", as_index=False).agg(
        units_sold=("quantity","sum"), revenue_mmk=("revenue_mmk","sum"),
        estimated_cogs_mmk=("estimated_cogs_mmk","sum"), gross_profit_mmk=("gross_profit_mmk","sum"),
        transactions=("transaction_id","nunique"))
    perf = products.merge(perf, on="product_id", how="left")
    num_cols = ["units_sold","revenue_mmk","estimated_cogs_mmk","gross_profit_mmk","transactions"]
    perf[num_cols] = perf[num_cols].fillna(0)
    perf["gross_margin_pct"] = (perf.gross_profit_mmk / perf.revenue_mmk.replace(0, pd.NA)).fillna(0)
    perf["avg_daily_units"] = perf.units_sold / 30

    latest_counts = counts.sort_values("count_date").groupby("product_id").tail(1)[["product_id","count_date","counted_quantity"]]
    inv = products.merge(latest_counts, on="product_id", how="left")
    sales_after = sales.merge(latest_counts, on="product_id", how="left")
    sales_after = sales_after[sales_after.sale_datetime.dt.normalize() > sales_after.count_date]
    sold = sales_after.groupby("product_id").quantity.sum().rename("sold_after_count")
    buy_after = purchases.merge(latest_counts, on="product_id", how="left")
    buy_after = buy_after[buy_after.purchase_date > buy_after.count_date]
    bought = buy_after.groupby("product_id").quantity.sum().rename("bought_after_count")
    inv = inv.join(sold, on="product_id").join(bought, on="product_id").fillna({"sold_after_count":0,"bought_after_count":0})
    inv["estimated_stock"] = inv.counted_quantity + inv.bought_after_count - inv.sold_after_count
    inv = inv.merge(perf[["product_id","avg_daily_units"]], on="product_id", how="left").merge(suppliers[["supplier_id","lead_time_days"]], on="supplier_id", how="left")
    inv["safety_stock"] = (inv.avg_daily_units * 3).round().astype(int)
    inv["calculated_reorder_point"] = (inv.avg_daily_units * inv.lead_time_days + inv.safety_stock).round().astype(int)
    inv["effective_reorder_point"] = inv[["reorder_level","calculated_reorder_point"]].max(axis=1)
    inv["target_stock"] = (inv.avg_daily_units * (inv.lead_time_days + 10) + inv.safety_stock).round().astype(int)
    inv["suggested_reorder_qty"] = (inv.target_stock - inv.estimated_stock).clip(lower=0).round().astype(int)
    inv["stock_status"] = inv.apply(lambda r: "REORDER" if r.estimated_stock <= r.effective_reorder_point else "OK", axis=1)

    daily = sales.groupby(sales.sale_datetime.dt.date).agg(revenue_mmk=("revenue_mmk","sum"), gross_profit_mmk=("gross_profit_mmk","sum"), transactions=("transaction_id","nunique")).reset_index(names="sale_date")
    category = perf.groupby("category", as_index=False).agg(revenue_mmk=("revenue_mmk","sum"),gross_profit_mmk=("gross_profit_mmk","sum"),units_sold=("units_sold","sum")).sort_values("gross_profit_mmk",ascending=False)
    last5 = sales[sales.sale_datetime >= max_date - pd.Timedelta(days=4)]
    summary = {
        "as_of_date": str(max_date.date()),
        "last_5_day_revenue_mmk": int(last5.revenue_mmk.sum()),
        "last_5_day_gross_profit_mmk": int(last5.gross_profit_mmk.sum()),
        "last_5_day_transactions": int(last5.transaction_id.nunique()),
        "average_basket_mmk": round(last5.revenue_mmk.sum() / max(last5.transaction_id.nunique(),1)),
        "products_requiring_reorder": int((inv.stock_status == "REORDER").sum()),
        "products_tracked": int(len(products)),
    }
    perf.to_csv(OUT / "product_performance_30d.csv", index=False)
    inv.to_csv(OUT / "inventory_recommendations.csv", index=False)
    daily.to_csv(OUT / "daily_performance.csv", index=False)
    category.to_csv(OUT / "category_performance_30d.csv", index=False)
    (OUT / "management_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    products = pd.read_csv(RAW / "products.csv")
    suppliers = pd.read_csv(RAW / "suppliers.csv")
    raw_sales = pd.read_csv(RAW / "sales.csv")
    raw_purchases = pd.read_csv(RAW / "purchases.csv")
    raw_counts = pd.read_csv(RAW / "inventory_counts.csv")
    product_ids, supplier_ids = set(products.product_id), set(suppliers.supplier_id)
    sales, rejected_sales = validate_sales(raw_sales, product_ids)
    purchases, rejected_purchases = validate_purchases(raw_purchases, product_ids, supplier_ids)
    counts, rejected_counts = validate_counts(raw_counts, product_ids)
    for name, frame in [("sales_clean.csv",sales),("purchases_clean.csv",purchases),("inventory_counts_clean.csv",counts),("rejected_sales.csv",rejected_sales),("rejected_purchases.csv",rejected_purchases),("rejected_inventory_counts.csv",rejected_counts)]:
        frame.to_csv(OUT / name, index=False)
    summary = build_outputs(products, suppliers, sales, purchases, counts)
    quality = pd.DataFrame([
        ("sales",len(raw_sales),len(sales),len(rejected_sales)),
        ("purchases",len(raw_purchases),len(purchases),len(rejected_purchases)),
        ("inventory_counts",len(raw_counts),len(counts),len(rejected_counts)),
    ], columns=["dataset","received_rows","accepted_rows","rejected_rows"])
    quality["acceptance_rate"] = quality.accepted_rows / quality.received_rows
    quality.to_csv(OUT / "data_quality_summary.csv", index=False)
    print(json.dumps(summary, indent=2))
    print(quality.to_string(index=False))

if __name__ == "__main__":
    main()

