CREATE OR REPLACE VIEW cleaned AS
SELECT * FROM read_csv_auto('{{cleaned_path}}');

SELECT 'duplicate_business_keys' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT order_id, product_id, order_date
    FROM cleaned
    GROUP BY order_id, product_id, order_date
    HAVING COUNT(*) > 1
) t

UNION ALL

SELECT 'missing_order_id' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE order_id IS NULL OR order_id = ''

UNION ALL

SELECT 'missing_product_id' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE product_id IS NULL OR product_id = ''

UNION ALL

SELECT 'invalid_quantity' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE quantity IS NULL OR CAST(quantity AS DOUBLE) <= 0

UNION ALL

SELECT 'invalid_unit_price' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE unit_price IS NULL OR CAST(unit_price AS DOUBLE) <= 0

UNION ALL

SELECT 'invalid_discount' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE discount IS NULL OR CAST(discount AS DOUBLE) < 0 OR CAST(discount AS DOUBLE) > 0.80

UNION ALL

SELECT 'bad_email_format' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE customer_email IS NOT NULL
  AND customer_email != ''
  AND customer_email NOT LIKE '%@%.%'

UNION ALL

SELECT 'date_out_of_range' AS check_name, COUNT(*) AS issue_count
FROM cleaned
WHERE CAST(order_date AS DATE) < CAST('2010-01-01' AS DATE)
   OR CAST(order_date AS DATE) > CURRENT_DATE;
