import sys
import unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pipeline import validate_sales, validate_purchases, validate_counts

class PipelineTests(unittest.TestCase):
    def test_sales_rejects_invalid_rows_and_calculates_profit(self):
        df = pd.DataFrame([
            ["SL1","T1","2026-01-01 10:00","P001",2,1000,700,0,"Cash"],
            ["SL2","T2","2026-01-01 11:00","P999",1,1000,700,0,"Cash"],
            ["SL3","T3","2026-01-01 12:00","P001",-1,1000,700,0,"Cash"],
        ], columns=["sale_line_id","transaction_id","sale_datetime","product_id","quantity","unit_selling_price","unit_cost","discount_mmk","payment_method"])
        clean, rejected = validate_sales(df, {"P001"})
        self.assertEqual(len(clean), 1)
        self.assertEqual(len(rejected), 2)
        self.assertEqual(clean.iloc[0].revenue_mmk, 2000)
        self.assertEqual(clean.iloc[0].gross_profit_mmk, 600)

    def test_purchase_rejects_unknown_supplier(self):
        df = pd.DataFrame([["PL1","PO1","2026-01-01","S99","P001",5,500]], columns=["purchase_line_id","purchase_id","purchase_date","supplier_id","product_id","quantity","unit_purchase_price"])
        clean, rejected = validate_purchases(df,{"P001"},{"S01"})
        self.assertTrue(clean.empty)
        self.assertEqual(rejected.iloc[0].rejection_reason,"unknown_supplier_id")

    def test_inventory_allows_zero_but_rejects_negative(self):
        df = pd.DataFrame([["IC1","2026-01-01","P001",0],["IC2","2026-01-01","P001",-1]], columns=["count_id","count_date","product_id","counted_quantity"])
        clean, rejected = validate_counts(df,{"P001"})
        self.assertEqual(len(clean),1)
        self.assertEqual(len(rejected),1)

if __name__ == "__main__":
    unittest.main()
