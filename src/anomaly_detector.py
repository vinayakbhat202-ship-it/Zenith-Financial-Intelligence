import os
import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "zenith.db")

BENFORD_EXPECTED = {
    1: 0.3010,
    2: 0.1761,
    3: 0.1249,
    4: 0.0969,
    5: 0.0792,
    6: 0.0669,
    7: 0.0580,
    8: 0.0512,
    9: 0.0458
}

def get_leading_digit(amount):
    abs_amt = abs(amount)
    if abs_amt == 0:
        return None
    s = f"{abs_amt:.6f}".replace(".", "").lstrip("0")
    if s:
        return int(s[0])
    return None

def compute_benford_deviations(df):
    """
    Computes Benford's Law deviations per user based on their transaction history.
    """
    print("Computing Benford's Law deviation profiles...")
    
    # Extract leading digits
    df["leading_digit"] = df["amount"].apply(get_leading_digit)
    
    # Calculate digit frequencies per poster
    # For users with very few postings, default to base frequencies
    user_digit_counts = df.groupby(["posted_by", "leading_digit"]).size().unstack(fill_value=0)
    user_totals = user_digit_counts.sum(axis=1)
    
    # Convert to frequencies
    user_digit_freqs = user_digit_counts.div(user_totals, axis=0)
    
    deviations = []
    for idx, row in df.iterrows():
        poster = row["posted_by"]
        digit = row["leading_digit"]
        
        if pd.isna(digit) or digit not in BENFORD_EXPECTED:
            deviations.append(0.0)
            continue
            
        # Get poster's actual frequency for this digit
        if poster in user_digit_freqs.index and user_totals[poster] >= 5:
            actual_freq = user_digit_freqs.loc[poster, digit]
        else:
            # Fallback to standard global counts if user has sparse history
            actual_freq = BENFORD_EXPECTED[digit]
            
        # Deviation calculation
        expected_freq = BENFORD_EXPECTED[digit]
        dev = abs(actual_freq - expected_freq) * 100.0
        deviations.append(dev)
        
    return deviations

def train_isolation_forest(df):
    """
    Trains an Isolation Forest model to flag structural anomalies.
    """
    print("Training Isolation Forest Anomaly Detection model...")
    
    # Prepare features
    features_df = pd.DataFrame()
    features_df["log_amount"] = np.log1p(df["amount"])
    features_df["hour"] = df["datetime"].dt.hour
    features_df["day_of_week"] = df["datetime"].dt.dayofweek
    features_df["is_manual_override"] = df["is_manual_override"]
    features_df["is_sod_violation"] = (df["posted_by"] == df["approved_by"]).astype(int)
    
    # One-hot encoding categorical accounts & users
    encoded_accounts = pd.get_dummies(df["account_class"], prefix="acct_class")
    encoded_users = pd.get_dummies(df["posted_by"], prefix="user")
    
    X = pd.concat([features_df, encoded_accounts, encoded_users], axis=1)
    
    # Handle NaN values if any
    X = X.fillna(0)
    
    # Fit Isolation Forest
    model = IsolationForest(contamination=0.03, random_state=42)
    model.fit(X)
    
    # Negative anomaly scores: lower values represent typical records, higher represent outliers
    raw_scores = -model.score_samples(X)
    
    # Standardize anomaly scores between 0 and 1
    min_score = np.min(raw_scores)
    max_score = np.max(raw_scores)
    if max_score > min_score:
        scaled_scores = (raw_scores - min_score) / (max_score - min_score)
    else:
        scaled_scores = np.zeros_like(raw_scores)
        
    return scaled_scores

def run_anomaly_detection():
    print(f"Loading transaction records from: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT fje.entry_key, fje.entry_id, fje.transaction_date, fje.posted_by, fje.approved_by, 
               fje.debit_amount, fje.credit_amount, fje.is_manual_override,
               da.account_class
        FROM fact_journal_entries fje
        JOIN dim_accounts da ON fje.account_key = da.account_key
    """
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("No transactions found.")
        conn.close()
        return
        
    # Process dates & amount representation
    df["datetime"] = pd.to_datetime(df["transaction_date"])
    df["amount"] = df["debit_amount"] + df["credit_amount"]
    
    # 1. Compute Benford deviations
    benford_devs = compute_benford_deviations(df)
    df["benford_deviation"] = benford_devs
    
    # 2. Compute Isolation Forest Scores
    if len(df) >= 10:
        anomaly_scores = train_isolation_forest(df)
    else:
        anomaly_scores = np.zeros(len(df))
    df["anomaly_score"] = anomaly_scores
    
    # 3. Compute final Risk score (0 - 100 scale)
    # Give high weight to Benford deviations if they are major anomalies, and Isolation Forest
    df["risk_score"] = (df["anomaly_score"] * 60) + (df["benford_deviation"] * 4)
    df["risk_score"] = df["risk_score"].clip(0, 100)
    
    # Update SQLite database
    print("Writing anomaly scores back to database...")
    cursor = conn.cursor()
    
    updates = []
    for idx, row in df.iterrows():
        updates.append((
            float(row["anomaly_score"]),
            float(row["benford_deviation"]),
            float(row["risk_score"]),
            int(row["entry_key"])
        ))
        
    cursor.executemany(
        """UPDATE fact_journal_entries 
           SET anomaly_score = ?, benford_deviation = ?, risk_score = ? 
           WHERE entry_key = ?""",
        updates
    )
    
    conn.commit()
    print("Database anomaly scores updated.")
    
    # Display top anomalies for verification
    print("\n--- Top Flagged Anomalies ---")
    df_sorted = df.sort_values(by="risk_score", ascending=False).head(10)
    for idx, row in df_sorted.iterrows():
        print(f"Entry: {row['entry_id']} | Date: {row['transaction_date']} | Posted By: {row['posted_by']} | "
              f"Amount: ${row['amount']:.2f} | Risk Score: {row['risk_score']:.1f}")
        
    conn.close()

if __name__ == "__main__":
    run_anomaly_detection()
