CREATE OR REPLACE VIEW cleaned AS
SELECT * FROM read_csv_auto('{{cleaned_path}}');

SELECT 'total_valid_records' AS metric, CAST(COUNT(*) AS VARCHAR) AS value
FROM cleaned;

SELECT 'total_sales' AS metric, CAST(SUM(total_amount) AS VARCHAR) AS value
FROM cleaned
WHERE is_revenue_realized = true;

SELECT
    DATE_TRUNC('month', CAST(order_date AS DATE)) AS month,
    SUM(total_amount) AS revenue,
    COUNT(*) AS record_count
FROM cleaned
WHERE is_revenue_realized = true
GROUP BY 1
ORDER BY 1;

SELECT
    category,
    SUM(total_amount) AS revenue,
    COUNT(*) AS record_count
FROM cleaned
WHERE is_revenue_realized = true
GROUP BY category
ORDER BY revenue DESC;

SELECT
    country,
    SUM(total_amount) AS revenue,
    COUNT(*) AS record_count
FROM cleaned
WHERE is_revenue_realized = true
GROUP BY country
ORDER BY revenue DESC;

SELECT
    product_name,
    SUM(quantity) AS total_quantity,
    SUM(total_amount) AS revenue
FROM cleaned
WHERE is_revenue_realized = true
GROUP BY product_name
ORDER BY total_quantity DESC
LIMIT 10;

SELECT 'average_order_value' AS metric, CAST(AVG(total_amount) AS VARCHAR) AS value
FROM cleaned
WHERE is_revenue_realized = true;
