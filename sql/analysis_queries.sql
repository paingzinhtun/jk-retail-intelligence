-- 1. Daily revenue and gross profit: review the trading trend.
SELECT sale_datetime::date AS sale_date,
       SUM(quantity * unit_selling_price - discount_mmk) AS revenue_mmk,
       SUM(quantity * (unit_selling_price - unit_cost) - discount_mmk) AS gross_profit_mmk
FROM sales
GROUP BY sale_datetime::date
ORDER BY sale_date;

-- 2. Product performance: allocate attention and working capital.
SELECT *, ROUND(100.0 * gross_profit_mmk / NULLIF(revenue_mmk, 0), 1) AS gross_margin_pct
FROM vw_product_performance
ORDER BY gross_profit_mmk DESC;

-- 3. Category contribution: understand the shop's economic mix.
SELECT category, SUM(revenue_mmk) AS revenue_mmk, SUM(gross_profit_mmk) AS gross_profit_mmk
FROM vw_product_performance
GROUP BY category
ORDER BY gross_profit_mmk DESC;

-- 4. Recent fast movers: identify replenishment priorities.
SELECT p.product_id, p.product_name, SUM(s.quantity) AS units_last_30_days
FROM sales s
JOIN products p USING (product_id)
WHERE s.sale_datetime >= (SELECT MAX(sale_datetime) FROM sales) - INTERVAL '30 days'
GROUP BY p.product_id, p.product_name
ORDER BY units_last_30_days DESC;

-- 5. Slow movers: review cash tied in products with little movement.
SELECT p.product_id, p.product_name, COALESCE(SUM(s.quantity), 0) AS units_last_30_days
FROM products p
LEFT JOIN sales s ON p.product_id = s.product_id
 AND s.sale_datetime >= (SELECT MAX(sale_datetime) FROM sales) - INTERVAL '30 days'
GROUP BY p.product_id, p.product_name
HAVING COALESCE(SUM(s.quantity), 0) <= 3
ORDER BY units_last_30_days, p.product_name;

-- 6. Average basket value: observe transaction economics.
SELECT ROUND(SUM(quantity * unit_selling_price - discount_mmk)::numeric /
             NULLIF(COUNT(DISTINCT transaction_id), 0), 0) AS average_basket_value_mmk
FROM sales;

-- 7. Five-day cycle summary: match the retailer's current review rhythm.
SELECT date_trunc('day', MIN(sale_datetime))::date AS first_date,
       date_trunc('day', MAX(sale_datetime))::date AS last_date,
       COUNT(DISTINCT transaction_id) AS transactions,
       SUM(quantity * unit_selling_price - discount_mmk) AS revenue_mmk,
       SUM(quantity * (unit_selling_price - unit_cost) - discount_mmk) AS gross_profit_mmk
FROM sales
WHERE sale_datetime >= (SELECT MAX(sale_datetime)::date - 4 FROM sales);

