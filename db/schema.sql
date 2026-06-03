-- SQLite Database Schema for Zenith Unified Enterprise Platform

-- 1. FINANCIAL AUDIT TABLES
CREATE TABLE IF NOT EXISTS dim_accounts (
    account_key INTEGER PRIMARY KEY AUTOINCREMENT,
    account_code TEXT UNIQUE NOT NULL,
    account_name TEXT NOT NULL,
    account_class TEXT NOT NULL, -- Asset, Liability, Equity, Revenue, Expense
    account_subclass TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS dim_entities (
    entity_key INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_code TEXT UNIQUE NOT NULL,
    entity_name TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_users (
    user_key INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    department TEXT NOT NULL,
    clearance_level TEXT NOT NULL -- Standard, Manager, Auditor
);

CREATE TABLE IF NOT EXISTS fact_journal_entries (
    entry_key INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    account_key INTEGER REFERENCES dim_accounts(account_key),
    entity_key INTEGER REFERENCES dim_entities(entity_key),
    user_key INTEGER REFERENCES dim_users(user_key),
    transaction_date TEXT NOT NULL,
    debit_amount REAL DEFAULT 0.0,
    credit_amount REAL DEFAULT 0.0,
    is_manual_override INTEGER DEFAULT 0,
    posted_by TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    anomaly_score REAL DEFAULT 0.0,
    benford_deviation REAL DEFAULT 0.0,
    risk_score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS fact_audit_log (
    audit_key INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT UNIQUE NOT NULL,
    audit_date TEXT NOT NULL,
    analyst_status TEXT DEFAULT 'PENDING',
    llm_determination TEXT,
    llm_audit_summary TEXT
);

-- 2. BRAND SENTIMENT TABLES (Hinglish/English social reviews)
CREATE TABLE IF NOT EXISTS dim_sentiment_channels (
    channel_key INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_name TEXT NOT NULL, -- Twitter, Reddit, YouTube
    author_handle TEXT NOT NULL,
    follower_cohort TEXT
);

CREATE TABLE IF NOT EXISTS fact_brand_reviews (
    review_key INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id TEXT UNIQUE NOT NULL,
    channel_key INTEGER REFERENCES dim_sentiment_channels(channel_key),
    raw_text TEXT NOT NULL,
    normalized_text TEXT,
    sentiment_label TEXT, -- Positive, Negative, Neutral
    confidence_score REAL,
    post_timestamp TEXT NOT NULL
);

-- 3. COMPETITOR MARKET & PRICING TABLES (Dark patterns tracking)
CREATE TABLE IF NOT EXISTS dim_competitor_retailers (
    retailer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer_name TEXT UNIQUE NOT NULL,
    domain_url TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_retail_prices (
    price_key INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer_key INTEGER REFERENCES dim_competitor_retailers(retailer_key),
    product_sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    cart_price REAL NOT NULL,
    checkout_price REAL NOT NULL,
    price_inflation_pct REAL NOT NULL,
    is_violation INTEGER DEFAULT 0, -- 1 if checkout_price > cart_price (drip pricing)
    violation_category TEXT,       -- DRIP_PRICING, HIDDEN_FEES, FAKE_SCARCITY
    timestamp TEXT NOT NULL
);

-- Performance indices
CREATE INDEX IF NOT EXISTS idx_fje_entry_id ON fact_journal_entries(entry_id);
CREATE INDEX IF NOT EXISTS idx_fje_date ON fact_journal_entries(transaction_date);
CREATE INDEX IF NOT EXISTS idx_fbr_comment ON fact_brand_reviews(comment_id);
CREATE INDEX IF NOT EXISTS idx_frp_sku ON fact_retail_prices(product_sku);
