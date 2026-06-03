-- Forensic Analytical Queries for Zenith General Ledger

-- 1. DOUBLE-ENTRY INTEGRITY CHECK
-- Purpose: Ensures debits equal credits for every transaction ID. Any imbalance is an error.
SELECT 
    entry_id,
    SUM(debit_amount) AS total_debit,
    SUM(credit_amount) AS total_credit,
    SUM(debit_amount) - SUM(credit_amount) AS discrepancy
FROM fact_journal_entries
GROUP BY entry_id
HAVING discrepancy <> 0;


-- 2. SEPARATION OF DUTIES (SoD) VIOLATION LOG
-- Purpose: Finds transactions posted and approved by the exact same user.
SELECT 
    fje.entry_id,
    fje.transaction_date,
    fje.posted_by,
    fje.approved_by,
    da.account_code,
    da.account_name,
    (fje.debit_amount + fje.credit_amount) AS transaction_amount,
    fje.risk_score
FROM fact_journal_entries fje
JOIN dim_accounts da ON fje.account_key = da.account_key
WHERE fje.posted_by = fje.approved_by AND (fje.debit_amount > 0 OR fje.credit_amount > 0)
ORDER BY transaction_amount DESC;


-- 3. TRANSACTION SPLITTING PATTERN DETECTOR
-- Purpose: Identifies cases where a user posted multiple entries below the $5,000 threshold 
-- to the same account on the same day, potentially trying to bypass approval limits.
WITH daily_postings AS (
    SELECT 
        DATE(transaction_date) AS post_date,
        posted_by,
        account_key,
        COUNT(DISTINCT entry_id) AS split_count,
        SUM(debit_amount + credit_amount) AS total_daily_value,
        GROUP_CONCAT(entry_id) AS split_entry_ids
    FROM fact_journal_entries
    WHERE (debit_amount + credit_amount) < 5000.0 -- Under threshold
      AND (debit_amount + credit_amount) > 0
    GROUP BY post_date, posted_by, account_key
)
SELECT 
    dp.post_date,
    dp.posted_by,
    da.account_code,
    da.account_name,
    dp.split_count,
    dp.total_daily_value,
    dp.split_entry_ids
FROM daily_postings dp
JOIN dim_accounts da ON dp.account_key = da.account_key
WHERE dp.split_count >= 3 -- 3 or more split entries in a single day
ORDER BY dp.total_daily_value DESC;


-- 4. OFF-HOURS TRANSACTION LOG (Rule 103 Compliance)
-- Purpose: Extract manual transactions posted outside core working hours (9 AM - 6 PM)
-- or on weekends, excluding system automated process accounts.
SELECT 
    fje.entry_id,
    fje.transaction_date,
    fje.posted_by,
    du.clearance_level,
    (fje.debit_amount + fje.credit_amount) AS transaction_amount,
    da.account_name,
    -- Extract hour from SQLite date string (Format: YYYY-MM-DD HH:MM:SS)
    STRFTIME('%H', fje.transaction_date) AS posting_hour,
    -- Extract day of week (0=Sunday, 6=Saturday in standard, SQLite has different values: 0-6 where 0 is Sunday)
    STRFTIME('%w', fje.transaction_date) AS day_of_week
FROM fact_journal_entries fje
JOIN dim_users du ON fje.user_key = du.user_key
JOIN dim_accounts da ON fje.account_key = da.account_key
WHERE du.user_id <> 'usr_admin' -- Exclude automated processes
  AND (
      STRFTIME('%H', fje.transaction_date) < '09' 
      OR STRFTIME('%H', fje.transaction_date) >= '18'
      OR STRFTIME('%w', fje.transaction_date) IN ('0', '6')
  )
ORDER BY transaction_date DESC;


-- 5. EXECUTIVE AUDIT PROGRESS SUMMARY
-- Purpose: Overview of total transactions audited, pending reviews, and severity levels.
SELECT 
    COALESCE(fal.llm_determination, 'UNASSIGNED/NOT_ANOMALOUS') AS audit_determination,
    COUNT(DISTINCT fje.entry_id) AS transaction_count,
    SUM(fje.debit_amount + fje.credit_amount) / 2 AS total_value_affected,
    AVG(fje.risk_score) AS average_risk_score
FROM fact_journal_entries fje
LEFT JOIN fact_audit_log fal ON fje.entry_id = fal.entry_id
GROUP BY audit_determination;
