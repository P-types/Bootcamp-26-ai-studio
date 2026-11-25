\set ON_ERROR_STOP on

-- Create the practice table. This dataset contains synthetic training records only.
CREATE TABLE IF NOT EXISTS vendor_payments (
    payment_id TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    payment_date DATE,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    payment_status TEXT NOT NULL CHECK (payment_status IN ('paid', 'pending'))
);

-- Stage and upsert the CSV so rerunning this file does not duplicate sample rows.
CREATE TEMP TABLE vendor_payments_import (LIKE vendor_payments);
\copy vendor_payments_import FROM 'vendor_payments.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO vendor_payments (
    payment_id, vendor_id, vendor_name, invoice_number, invoice_date,
    due_date, payment_date, amount, currency, payment_status
)
SELECT
    payment_id, vendor_id, vendor_name, invoice_number, invoice_date,
    due_date, payment_date, amount, currency, payment_status
FROM vendor_payments_import
ON CONFLICT (payment_id) DO NOTHING;
DROP TABLE vendor_payments_import;

ANALYZE vendor_payments;

-- Index comparison, before: inspect the plan for a vendor-filtered lookup.
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM vendor_payments
WHERE vendor_id = 'V001';

-- 1. Which vendors have the highest total invoiced spend?
SELECT vendor_id, vendor_name, SUM(amount) AS total_invoiced, COUNT(*) AS invoice_count
FROM vendor_payments
GROUP BY vendor_id, vendor_name
ORDER BY total_invoiced DESC;

-- 2. Which invoice records are duplicates for the same vendor and invoice number?
WITH ranked_invoices AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY vendor_id, invoice_number
            ORDER BY payment_date NULLS LAST, payment_id
        ) AS invoice_row
    FROM vendor_payments
)
SELECT vendor_id, vendor_name, invoice_number, payment_id, amount, payment_date
FROM ranked_invoices
WHERE invoice_row > 1
ORDER BY vendor_id, invoice_number, payment_id;

-- 3. What is the total invoiced amount by invoice month?
SELECT DATE_TRUNC('month', invoice_date)::date AS invoice_month,
       SUM(amount) AS monthly_invoiced
FROM vendor_payments
GROUP BY DATE_TRUNC('month', invoice_date)
ORDER BY invoice_month;

-- 4. Which payments were made after their due date, and how late were they?
SELECT payment_id, vendor_name, invoice_number, due_date, payment_date,
       payment_date - due_date AS days_late, amount
FROM vendor_payments
WHERE payment_date > due_date
ORDER BY days_late DESC, payment_id;

-- 5. How much remains unpaid by vendor?
SELECT vendor_id, vendor_name, COUNT(*) AS unpaid_invoice_count,
       SUM(amount) AS unpaid_amount
FROM vendor_payments
WHERE payment_status = 'pending'
GROUP BY vendor_id, vendor_name
ORDER BY unpaid_amount DESC;

-- 6. How many days does each vendor take to get paid on average?
SELECT vendor_id, vendor_name,
       ROUND(AVG(payment_date - invoice_date), 1) AS avg_days_to_payment
FROM vendor_payments
WHERE payment_date IS NOT NULL
GROUP BY vendor_id, vendor_name
ORDER BY avg_days_to_payment DESC;

-- 7. What percentage of total invoiced spend belongs to each vendor?
WITH vendor_totals AS (
    SELECT vendor_id, vendor_name, SUM(amount) AS total_invoiced
    FROM vendor_payments
    GROUP BY vendor_id, vendor_name
)
SELECT vendor_id, vendor_name, total_invoiced,
       ROUND(100.0 * total_invoiced / SUM(total_invoiced) OVER (), 2) AS spend_share_pct
FROM vendor_totals
ORDER BY spend_share_pct DESC;

-- 8. How many invoices and dollars are in each payment status?
SELECT payment_status, COUNT(*) AS invoice_count, SUM(amount) AS total_amount
FROM vendor_payments
GROUP BY payment_status
ORDER BY payment_status;

-- 9. Which invoices are at least $10,000?
SELECT payment_id, vendor_name, invoice_number, amount, payment_status
FROM vendor_payments
WHERE amount >= 10000
ORDER BY amount DESC, payment_id;

-- 10. Which vendors lead each month by invoiced spend?
WITH monthly_vendor_spend AS (
    SELECT DATE_TRUNC('month', invoice_date)::date AS invoice_month,
           vendor_id, vendor_name, SUM(amount) AS monthly_spend
    FROM vendor_payments
    GROUP BY DATE_TRUNC('month', invoice_date), vendor_id, vendor_name
)
SELECT invoice_month, vendor_id, vendor_name, monthly_spend,
       RANK() OVER (PARTITION BY invoice_month ORDER BY monthly_spend DESC) AS spend_rank
FROM monthly_vendor_spend
ORDER BY invoice_month, spend_rank, vendor_id;

-- Add an index for vendor-filtered lookups and refresh planner statistics.
CREATE INDEX IF NOT EXISTS vendor_payments_vendor_id_idx
    ON vendor_payments (vendor_id);
ANALYZE vendor_payments;

-- Index comparison, after: compare this plan with the earlier EXPLAIN output.
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM vendor_payments
WHERE vendor_id = 'V001';