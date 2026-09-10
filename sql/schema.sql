DROP VIEW IF EXISTS vw_product_performance;
DROP TABLE IF EXISTS inventory_counts, purchases, sales, products, suppliers CASCADE;

CREATE TABLE suppliers (
    supplier_id text PRIMARY KEY CHECK (supplier_id ~ '^S[0-9]{2}$'),
    supplier_name text NOT NULL,
    township text NOT NULL,
    lead_time_days integer NOT NULL CHECK (lead_time_days BETWEEN 1 AND 14),
    minimum_order_mmk integer NOT NULL CHECK (minimum_order_mmk >= 0)
);

CREATE TABLE products (
    product_id text PRIMARY KEY CHECK (product_id ~ '^P[0-9]{3}$'),
    product_name text NOT NULL,
    category text NOT NULL,
    unit text NOT NULL,
    default_purchase_price integer NOT NULL CHECK (default_purchase_price > 0),
    default_selling_price integer NOT NULL CHECK (default_selling_price > 0),
    supplier_id text NOT NULL REFERENCES suppliers(supplier_id),
    reorder_level integer NOT NULL CHECK (reorder_level >= 0),
    active boolean NOT NULL DEFAULT true
);

CREATE TABLE sales (
    sale_line_id text PRIMARY KEY,
    transaction_id text NOT NULL,
    sale_datetime timestamp NOT NULL,
    product_id text NOT NULL REFERENCES products(product_id),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_selling_price integer NOT NULL CHECK (unit_selling_price > 0),
    unit_cost integer NOT NULL CHECK (unit_cost > 0),
    discount_mmk integer NOT NULL DEFAULT 0 CHECK (discount_mmk >= 0),
    payment_method text NOT NULL CHECK (payment_method IN ('Cash','KBZPay','WavePay')),
    CHECK (discount_mmk < quantity * unit_selling_price)
);

CREATE TABLE purchases (
    purchase_line_id text PRIMARY KEY,
    purchase_id text NOT NULL,
    purchase_date date NOT NULL,
    supplier_id text NOT NULL REFERENCES suppliers(supplier_id),
    product_id text NOT NULL REFERENCES products(product_id),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_purchase_price integer NOT NULL CHECK (unit_purchase_price > 0)
);

CREATE TABLE inventory_counts (
    count_id text PRIMARY KEY,
    count_date date NOT NULL,
    product_id text NOT NULL REFERENCES products(product_id),
    counted_quantity integer NOT NULL CHECK (counted_quantity >= 0)
);

CREATE INDEX idx_sales_datetime ON sales(sale_datetime);
CREATE INDEX idx_sales_product ON sales(product_id);
CREATE INDEX idx_purchases_date ON purchases(purchase_date);

CREATE VIEW vw_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(s.quantity) AS units_sold,
    SUM(s.quantity * s.unit_selling_price - s.discount_mmk) AS revenue_mmk,
    SUM(s.quantity * s.unit_cost) AS estimated_cogs_mmk,
    SUM(s.quantity * (s.unit_selling_price - s.unit_cost) - s.discount_mmk) AS gross_profit_mmk
FROM products p
JOIN sales s USING (product_id)
GROUP BY p.product_id, p.product_name, p.category;

