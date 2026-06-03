import os
import sqlite3
import random
import uuid
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "zenith.db")

# Setup seed for reproducibility
random.seed(42)

ACCOUNTS = [
    ("1010", "Cash and Cash Equivalents", "Asset", "Cash"),
    ("1020", "Accounts Receivable", "Asset", "Receivables"),
    ("1050", "Prepaid Insurance", "Asset", "Prepayments"),
    ("1100", "Inventory", "Asset", "Inventory"),
    ("2010", "Accounts Payable", "Liability", "Payables"),
    ("2020", "Accrued Payroll", "Liability", "Accrued Liabilities"),
    ("2050", "Short-Term Debt", "Liability", "Debt"),
    ("3010", "Retained Earnings", "Equity", "Equity Retained"),
    ("3020", "Common Stock", "Equity", "Equity Shares"),
    ("4010", "Product Sales Revenue", "Revenue", "Sales"),
    ("4020", "Service Fee Revenue", "Revenue", "Services"),
    ("5010", "Cost of Goods Sold", "Expense", "COGS"),
    ("5020", "Office Rent Expense", "Expense", "Rent"),
    ("5030", "Employee Salaries Expense", "Expense", "Salaries"),
    ("5040", "Travel & Entertainment Expense", "Expense", "Travel"),
    ("5050", "IT Software & Subscriptions", "Expense", "Software"),
]

ENTITIES = [
    ("US-01", "US Operations Inc", "United States"),
    ("IN-01", "India Services Pvt Ltd", "India"),
    ("UK-01", "UK Logistics Ltd", "United Kingdom"),
]

USERS = [
    ("usr_admin", "System Automated Ledger", "Finance-IT", "Auditor"),
    ("usr_amit", "Amit Sharma", "Finance-India", "Standard"),
    ("usr_sarah", "Sarah Jenkins", "Finance-US", "Standard"),
    ("usr_john", "John Sterling", "Finance-UK", "Standard"),
    ("usr_priya", "Priya Patel", "Finance-India", "Manager"),
    ("usr_robert", "Robert Vance", "Finance-US", "Manager"),
]

# --- BRAND REVIEWS MOCK DATA ---
CHANNELS = [
    ("Twitter", "@sharma_finance", "Large"),
    ("Twitter", "@techi_guy", "Medium"),
    ("Reddit", "r/india_finance", "Large"),
    ("Reddit", "r/complaints_board", "Small"),
    ("YouTube", "FinTechGuru Reviews", "Medium"),
]

BRAND_REVIEWS = [
    # Positive Hinglish
    ("yaar ye zenith service ekdum mast hai! support fast tha.", "positive", 0.96),
    ("super software! integration bahut smooth tha, highly recommended.", "positive", 0.94),
    ("overall service acchi hai, pricing checks normal hai.", "positive", 0.88),
    ("kam budget me badhiya system! audit logs display transparent hai.", "positive", 0.91),
    # Negative Hinglish
    ("bahut bekaar service! checkout billing interface hangs repeatedly.", "negative", 0.98),
    ("yaar pricing check ki, and hidden fees are too high, bad experience.", "negative", 0.95),
    ("finance checks fail ho rahe hai constantly, not happy at all.", "negative", 0.92),
    ("amit approved his own invoices, SoD alert design are useless.", "negative", 0.89),
    # Neutral/Mixed Hinglish
    ("the pricing is okay okay, not too good, not too bad.", "neutral", 0.65),
    ("ledger entries are loading slowly today, hope they fix it.", "neutral", 0.70),
    ("customer dashboard works, but reports generation holds issues.", "neutral", 0.62),
    ("just signed up, will test the transaction ledger audit capabilities.", "neutral", 0.75),
    # English reviews
    ("Excellent compliance platform, double-entry ledgers balanced cleanly.", "positive", 0.99),
    ("Highly disappointed with the transaction delays in global offices.", "negative", 0.97),
    ("Average performance, standard charts could be more detailed.", "neutral", 0.60),
]

# --- COMPETITOR PRICING DATA ---
COMPETITORS = [
    ("Croma", "www.croma.com", "India"),
    ("Reliance Digital", "www.reliancedigital.in", "India"),
    ("Vijay Sales", "www.vijaysales.com", "India"),
]

PRODUCTS = [
    ("iphone-17", "Apple iPhone 17 Pro Max 256GB", 1199.00),
    ("ipad-pro", "Apple iPad Pro M4 11-inch", 999.00),
    ("macbook-air", "Apple MacBook Air M3 16GB", 1299.00),
]

def seed_static_dimensions(cursor):
    # Insert Accounts
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_accounts (account_code, account_name, account_class, account_subclass) VALUES (?, ?, ?, ?)",
        ACCOUNTS
    )
    # Insert Entities
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_entities (entity_code, entity_name, country) VALUES (?, ?, ?)",
        ENTITIES
    )
    # Insert Users
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_users (user_id, username, department, clearance_level) VALUES (?, ?, ?, ?)",
        USERS
    )
    # Insert Channels
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_sentiment_channels (platform_name, author_handle, follower_cohort) VALUES (?, ?, ?)",
        CHANNELS
    )
    # Insert Competitor Retailers
    cursor.executemany(
        "INSERT OR IGNORE INTO dim_competitor_retailers (retailer_name, domain_url, country) VALUES (?, ?, ?)",
        COMPETITORS
    )
    print("Static dimensions seeded.")

def generate_journal_entry(entry_id, date, entity_key, user_key, debit_acct, credit_acct, amount, posted_by, approved_by, is_override=0):
    debit_row = (entry_id, debit_acct, entity_key, user_key, date, amount, 0.0, is_override, posted_by, approved_by)
    credit_row = (entry_id, credit_acct, entity_key, user_key, date, 0.0, amount, is_override, posted_by, approved_by)
    return [debit_row, credit_row]

def generate_synthetic_ledger():
    print(f"Connecting to database to generate ledger at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Empty existing ledger
    cursor.execute("DELETE FROM fact_journal_entries")
    cursor.execute("DELETE FROM fact_audit_log")
    cursor.execute("DELETE FROM fact_brand_reviews")
    cursor.execute("DELETE FROM fact_retail_prices")
    
    # Load dimensions keys for mapping
    cursor.execute("SELECT account_key, account_code FROM dim_accounts")
    acct_map = {code: key for key, code in cursor.fetchall()}
    
    cursor.execute("SELECT entity_key, entity_code FROM dim_entities")
    entity_map = {code: key for key, code in cursor.fetchall()}
    
    cursor.execute("SELECT user_key, user_id FROM dim_users")
    user_map = {uid: key for key, uid in cursor.fetchall()}
    
    cursor.execute("SELECT channel_key, platform_name FROM dim_sentiment_channels")
    channel_map = {name: key for key, name in cursor.fetchall()}
    
    cursor.execute("SELECT retailer_key, retailer_name FROM dim_competitor_retailers")
    retailer_map = {name: key for key, name in cursor.fetchall()}
    
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 5, 30)
    current_date = start_date
    
    all_journal_entries = []
    all_brand_reviews = []
    all_retail_prices = []
    
    print("Generating standard business transactions...")
    while current_date <= end_date:
        num_transactions = random.randint(5, 12)
        for _ in range(num_transactions):
            entry_id = str(uuid.uuid4())[:8]
            hour = random.randint(9, 17)
            minute = random.randint(0, 59)
            trans_time = current_date.replace(hour=hour, minute=minute)
            date_str = trans_time.strftime("%Y-%m-%d %H:%M:%S")
            
            entity_code = random.choice(list(entity_map.keys()))
            entity_key = entity_map[entity_code]
            
            if entity_code == "IN-01":
                posted = "usr_amit"
                approved = "usr_priya"
            elif entity_code == "US-01":
                posted = "usr_sarah"
                approved = "usr_robert"
            else:
                posted = "usr_john"
                approved = "usr_robert"
                
            user_key = user_map[posted]
            
            tx_type = random.choice(["SALES", "EXPENSE", "PAYROLL", "INVENTORY"])
            if tx_type == "SALES":
                debit_acct = acct_map["1010"]
                credit_acct = acct_map["4010"]
                amount = round(random.uniform(500, 8000), 2)
            elif tx_type == "EXPENSE":
                debit_acct = acct_map["5050"]
                credit_acct = acct_map["1010"]
                amount = round(random.uniform(50, 1500), 2)
            elif tx_type == "PAYROLL":
                debit_acct = acct_map["5030"]
                credit_acct = acct_map["2020"]
                amount = round(random.uniform(2000, 6000), 2)
            else:
                debit_acct = acct_map["1100"]
                credit_acct = acct_map["2010"]
                amount = round(random.uniform(1000, 10000), 2)
                
            rows = generate_journal_entry(
                entry_id, date_str, entity_key, user_key, debit_acct, credit_acct, amount, posted, approved
            )
            all_journal_entries.extend(rows)
            
        current_date += timedelta(days=1)
        
    # --- SEEDING FORENSIC LEDGER ANOMALIES ---
    print("Seeding intentional forensic anomalies...")
    
    # 1. Off-hours
    for i in range(5):
        entry_id = f"ano_time_{i}"
        date_str = f"2026-03-12 02:45:{random.randint(10,59)}"
        entity_key = entity_map["US-01"]
        user_key = user_map["usr_sarah"]
        debit_acct = acct_map["5040"]
        credit_acct = acct_map["1010"]
        amount = round(random.uniform(4000, 8500), 2)
        rows = generate_journal_entry(
            entry_id, date_str, entity_key, user_key, debit_acct, credit_acct, amount, "usr_sarah", "usr_robert"
        )
        all_journal_entries.extend(rows)
        
    # 2. Separation of Duties (SoD)
    for i in range(3):
        entry_id = f"ano_sod_{i}"
        date_str = f"2026-04-18 14:20:00"
        entity_key = entity_map["IN-01"]
        user_key = user_map["usr_amit"]
        debit_acct = acct_map["1010"]
        credit_acct = acct_map["3020"]
        amount = round(random.uniform(15000, 30000), 2)
        rows = generate_journal_entry(
            entry_id, date_str, entity_key, user_key, debit_acct, credit_acct, amount, "usr_amit", "usr_amit", is_override=1
        )
        all_journal_entries.extend(rows)
        
    # 3. Transaction Splitting
    for i in range(2):
        split_date = f"2026-02-15 10:{20+i*5}:00"
        entity_key = entity_map["UK-01"]
        user_key = user_map["usr_john"]
        debit_acct = acct_map["5050"]
        credit_acct = acct_map["1010"]
        amount = 4999.00
        for j in range(3):
            entry_id = f"ano_split_{i}_{j}"
            rows = generate_journal_entry(
                entry_id, split_date, entity_key, user_key, debit_acct, credit_acct, amount, "usr_john", "usr_robert"
            )
            all_journal_entries.extend(rows)

    # 4. Benford digit outliers
    for i in range(12):
        entry_id = f"ano_benf_{i}"
        date_str = f"2026-05-02 11:32:00"
        entity_key = entity_map["US-01"]
        user_key = user_map["usr_sarah"]
        debit_acct = acct_map["5040"]
        credit_acct = acct_map["1010"]
        amount = float(f"999{random.randint(0,9)}.{random.randint(10,99)}")
        rows = generate_journal_entry(
            entry_id, date_str, entity_key, user_key, debit_acct, credit_acct, amount, "usr_sarah", "usr_robert"
        )
        all_journal_entries.extend(rows)

    # Write Journal Lines
    cursor.executemany(
        """INSERT INTO fact_journal_entries (
            entry_id, account_key, entity_key, user_key, transaction_date,
            debit_amount, credit_amount, is_manual_override, posted_by, approved_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        all_journal_entries
    )

    # --- SEEDING BRAND REVIEWS ---
    print("Seeding brand sentiment review feedback logs...")
    for i in range(60):
        channel_name = random.choice(list(channel_map.keys()))
        channel_key = channel_map[channel_name]
        
        # Pick a review text template
        text, sentiment, conf = random.choice(BRAND_REVIEWS)
        
        # Generate some text variations to make it realistic
        comment_id = f"review_{1000 + i}"
        post_time = (datetime.now() - timedelta(days=random.randint(0, 120))).strftime("%Y-%m-%d %H:%M:%S")
        
        all_brand_reviews.append((
            comment_id,
            channel_key,
            text,
            text.lower().strip(),
            sentiment,
            conf,
            post_time
        ))
        
    cursor.executemany(
        """INSERT INTO fact_brand_reviews (
            comment_id, channel_key, raw_text, normalized_text, sentiment_label, confidence_score, post_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        all_brand_reviews
    )

    # --- SEEDING COMPETITOR PRICES & VIOLATIONS ---
    print("Seeding competitor prices check events...")
    for i in range(100):
        competitor_name = random.choice(list(retailer_map.keys()))
        competitor_key = retailer_map[competitor_name]
        
        prod_sku, prod_name, base_price = random.choice(PRODUCTS)
        
        # Add random competitor dynamic variance
        cart_price = round(base_price * random.uniform(0.95, 1.05), 2)
        
        # 15% probability of drip pricing violation (checkout price higher than cart price)
        is_violation = 1 if random.random() < 0.15 else 0
        if is_violation:
            checkout_price = round(cart_price + random.uniform(20, 80), 2) # Hidden handling fees
            category = "DRIP_PRICING"
        else:
            checkout_price = cart_price
            category = None
            
        inflation_pct = round(((checkout_price - cart_price) / cart_price) * 100, 2)
        timestamp = (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        
        all_retail_prices.append((
            competitor_key,
            prod_sku,
            prod_name,
            cart_price,
            checkout_price,
            inflation_pct,
            is_violation,
            category,
            timestamp
        ))
        
    cursor.executemany(
        """INSERT INTO fact_retail_prices (
            retailer_key, product_sku, product_name, cart_price, checkout_price,
            price_inflation_pct, is_violation, violation_category, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        all_retail_prices
    )
    
    conn.commit()
    print(f"Generated {len(all_journal_entries)} entries in fact_journal_entries.")
    print(f"Generated {len(all_brand_reviews)} entries in fact_brand_reviews.")
    print(f"Generated {len(all_retail_prices)} entries in fact_retail_prices.")
    conn.close()

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    seed_static_dimensions(cursor)
    conn.commit()
    conn.close()
    generate_synthetic_ledger()
