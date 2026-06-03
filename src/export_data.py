import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "zenith.db")
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")

def export_table_to_csv(conn, table_name):
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    file_path = os.path.join(EXPORT_DIR, f"{table_name}.csv")
    df.to_csv(file_path, index=False)
    print(f"Exported {len(df)} rows from '{table_name}' table to: {file_path}")

def run_analytical_exports(conn):
    print("\nRunning analytical SQL queries and exporting views...")
    
    # 1. SoD Violations
    sod_query = """
        SELECT fje.entry_id, fje.transaction_date, fje.posted_by, fje.approved_by, 
               da.account_code, da.account_name, (fje.debit_amount + fje.credit_amount) AS amount, 
               fje.risk_score, fal.llm_determination, fal.llm_audit_summary
        FROM fact_journal_entries fje
        JOIN dim_accounts da ON fje.account_key = da.account_key
        LEFT JOIN fact_audit_log fal ON fje.entry_id = fal.entry_id
        WHERE fje.posted_by = fje.approved_by AND (fje.debit_amount > 0 OR fje.credit_amount > 0)
    """
    df_sod = pd.read_sql_query(sod_query, conn)
    df_sod.to_csv(os.path.join(EXPORT_DIR, "report_sod_violations.csv"), index=False)
    print(f"Exported {len(df_sod)} SoD violations.")

    # 2. Split Transactions
    split_query = """
        WITH daily_postings AS (
            SELECT 
                DATE(transaction_date) AS post_date,
                posted_by,
                account_key,
                COUNT(DISTINCT entry_id) AS split_count,
                SUM(debit_amount + credit_amount) AS total_daily_value,
                GROUP_CONCAT(entry_id) AS split_entry_ids
            FROM fact_journal_entries
            WHERE (debit_amount + credit_amount) < 5000.0
              AND (debit_amount + credit_amount) > 0
            GROUP BY post_date, posted_by, account_key
        )
        SELECT dp.post_date, dp.posted_by, da.account_code, da.account_name, 
               dp.split_count, dp.total_daily_value, dp.split_entry_ids
        FROM daily_postings dp
        JOIN dim_accounts da ON dp.account_key = da.account_key
        WHERE dp.split_count >= 3
    """
    df_split = pd.read_sql_query(split_query, conn)
    df_split.to_csv(os.path.join(EXPORT_DIR, "report_split_transactions.csv"), index=False)
    print(f"Exported {len(df_split)} split transaction cohorts.")

    # 3. Off-hours Postings
    offhours_query = """
        SELECT fje.entry_id, fje.transaction_date, fje.posted_by, du.clearance_level,
               (fje.debit_amount + fje.credit_amount) AS amount, da.account_name,
               STRFTIME('%H', fje.transaction_date) AS posting_hour,
               STRFTIME('%w', fje.transaction_date) AS day_of_week
        FROM fact_journal_entries fje
        JOIN dim_users du ON fje.user_key = du.user_key
        JOIN dim_accounts da ON fje.account_key = da.account_key
        WHERE du.user_id <> 'usr_admin'
          AND (
              STRFTIME('%H', fje.transaction_date) < '09' 
              OR STRFTIME('%H', fje.transaction_date) >= '18'
              OR STRFTIME('%w', fje.transaction_date) IN ('0', '6')
          )
    """
    df_off = pd.read_sql_query(offhours_query, conn)
    df_off.to_csv(os.path.join(EXPORT_DIR, "report_offhours_postings.csv"), index=False)
    print(f"Exported {len(df_off)} off-hours transaction records.")

    # 4. Sentiment Summary Report
    sentiment_query = """
        SELECT sentiment_label, COUNT(*) as review_count, AVG(confidence_score) as avg_confidence
        FROM fact_brand_reviews
        GROUP BY sentiment_label
    """
    df_sent = pd.read_sql_query(sentiment_query, conn)
    df_sent.to_csv(os.path.join(EXPORT_DIR, "report_sentiment_summary.csv"), index=False)
    print(f"Exported sentiment summary calculations.")

    # 5. Pricing Violations Report
    pricing_query = """
        SELECT dcr.retailer_name, COUNT(*) as checks_count,
               SUM(frp.is_violation) as violation_count,
               AVG(frp.price_inflation_pct) as avg_price_inflation
        FROM fact_retail_prices frp
        JOIN dim_competitor_retailers dcr ON frp.retailer_key = dcr.retailer_key
        GROUP BY dcr.retailer_name
    """
    df_pr = pd.read_sql_query(pricing_query, conn)
    df_pr.to_csv(os.path.join(EXPORT_DIR, "report_pricing_violations.csv"), index=False)
    print(f"Exported pricing compliance summary.")

def export_all():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        
    print(f"Exporting files to directory: {EXPORT_DIR}")
    conn = sqlite3.connect(DB_PATH)
    
    # Standard ledger dimensions
    export_table_to_csv(conn, "dim_accounts")
    export_table_to_csv(conn, "dim_entities")
    export_table_to_csv(conn, "dim_users")
    
    # Brand Sentiment and Competitor Retail dimensions
    export_table_to_csv(conn, "dim_sentiment_channels")
    export_table_to_csv(conn, "dim_competitor_retailers")
    
    # Fact tables
    export_table_to_csv(conn, "fact_journal_entries")
    export_table_to_csv(conn, "fact_audit_log")
    export_table_to_csv(conn, "fact_brand_reviews")
    export_table_to_csv(conn, "fact_retail_prices")
    
    # Reporting views
    run_analytical_exports(conn)
    
    conn.close()
    print("\nAll database tables successfully exported to CSVs!")

if __name__ == "__main__":
    export_all()
