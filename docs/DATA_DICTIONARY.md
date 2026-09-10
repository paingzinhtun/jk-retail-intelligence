# Data dictionary

## products

One row represents one sellable product/SKU.

| Field | Type | Required | Rule |
|---|---|---:|---|
| product_id | text | Yes | Unique; format P### |
| product_name | text | Yes | Nonblank |
| category | text | Yes | Controlled category |
| unit | text | Yes | Piece, pack, bottle, bag, etc. |
| default_purchase_price | integer MMK | Yes | Greater than zero |
| default_selling_price | integer MMK | Yes | Greater than zero |
| supplier_id | text | Yes | Must exist in suppliers |
| reorder_level | integer units | Yes | Zero or greater |
| active | boolean | Yes | True or False |

## suppliers

One row represents one supplier.

| Field | Type | Required | Rule |
|---|---|---:|---|
| supplier_id | text | Yes | Unique; format S## |
| supplier_name | text | Yes | Nonblank synthetic name |
| township | text | Yes | Nonblank |
| lead_time_days | integer | Yes | 1–14 days |
| minimum_order_mmk | integer MMK | Yes | Zero or greater |

## sales

One row represents one product line sold in one transaction.

| Field | Type | Required | Rule |
|---|---|---:|---|
| sale_line_id | text | Yes | Unique |
| transaction_id | text | Yes | Groups product lines in one basket |
| sale_datetime | datetime | Yes | Not in the future |
| product_id | text | Yes | Must exist in products |
| quantity | integer units | Yes | Greater than zero |
| unit_selling_price | integer MMK | Yes | Greater than zero |
| unit_cost | integer MMK | Yes | Greater than zero |
| discount_mmk | integer MMK | Yes | Zero or greater; below gross line value |
| payment_method | text | Yes | Cash, KBZPay, WavePay |

## purchases

One row represents one product line received from a supplier.

| Field | Type | Required | Rule |
|---|---|---:|---|
| purchase_line_id | text | Yes | Unique |
| purchase_id | text | Yes | Groups lines in one supplier order |
| purchase_date | date | Yes | Not in the future |
| supplier_id | text | Yes | Must exist in suppliers |
| product_id | text | Yes | Must exist in products |
| quantity | integer units | Yes | Greater than zero |
| unit_purchase_price | integer MMK | Yes | Greater than zero |

## inventory_counts

One row represents one product counted at one time.

| Field | Type | Required | Rule |
|---|---|---:|---|
| count_id | text | Yes | Unique |
| count_date | date | Yes | Not in the future |
| product_id | text | Yes | Must exist in products |
| counted_quantity | integer units | Yes | Zero or greater |

