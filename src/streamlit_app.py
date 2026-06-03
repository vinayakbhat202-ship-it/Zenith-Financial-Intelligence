import streamlit as st
import sqlite3
import pandas as pd
import os

# Page Config
st.set_page_config(
    page_title="Zenith Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a slightly cleaner look (but minimal, keeping it pure python)
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "zenith.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# Sidebar
st.sidebar.title("🛡️ Zenith")
st.sidebar.markdown("Enterprise Forensic Auditing Command Center")

# Fetch Global Stats
conn = get_db_connection()
stats_df = pd.read_sql_query("SELECT COUNT(*) as c FROM fact_journal_entries", conn)
total_entries = stats_df['c'][0]

audits_df = pd.read_sql_query("SELECT COUNT(*) as c FROM fact_audit_log", conn)
total_audits = audits_df['c'][0]

flagged_df = pd.read_sql_query("SELECT COUNT(*) as c FROM fact_journal_entries WHERE risk_score > 70", conn)
flagged_anomalies = flagged_df['c'][0]
unresolved = max(0, flagged_anomalies - total_audits)

reviews_df = pd.read_sql_query("SELECT COUNT(*) as c FROM fact_brand_reviews", conn)
total_reviews = reviews_df['c'][0]

market_df = pd.read_sql_query("SELECT COUNT(*) as c FROM fact_retail_prices", conn)
total_checks = market_df['c'][0]

violations_df = pd.read_sql_query("SELECT COUNT(*) as c FROM fact_retail_prices WHERE is_violation = 1", conn)
total_violations = violations_df['c'][0]

st.sidebar.markdown(f"**Platform Status:** Active 🟢")
st.sidebar.markdown("---")
st.sidebar.markdown("### System Health")
st.sidebar.markdown(f"- **Journal Lines Processed:** {total_entries:,}")
st.sidebar.markdown(f"- **AI Audits Logged:** {total_audits:,}")
st.sidebar.markdown(f"- **Unresolved Anomalies:** {unresolved:,}")

# Main Layout: Tabs
tab1, tab2, tab3 = st.tabs(["📈 Forensic Ledger", "💬 Brand Sentiment", "⚖️ Market Compliance"])

# ----------------- TAB 1: FORENSIC LEDGER -----------------
with tab1:
    st.header("Forensic Audit Dashboard")
    st.caption("AI-driven general ledger anomaly detection & RAG compliance verification")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("TOTAL LEDGER LINES", f"{total_entries:,}", "Ingestion Active")
    col2.metric("FLAGGED ANOMALIES", f"{flagged_anomalies:,}", "Risk > 70%", delta_color="inverse")
    col3.metric("AI AUDITS LOGGED", f"{total_audits:,}", "Verified by RAG")

    st.markdown("---")
    
    query = """
        SELECT fje.entry_id, fje.transaction_date, fje.posted_by, 
               (fje.debit_amount + fje.credit_amount) AS amount, fje.risk_score,
               da.account_class, fal.llm_determination, fal.llm_audit_summary
        FROM fact_journal_entries fje
        JOIN dim_accounts da ON fje.account_key = da.account_key
        LEFT JOIN fact_audit_log fal ON fje.entry_id = fal.entry_id
        WHERE fje.risk_score > 70.0
        ORDER BY fje.risk_score DESC
    """
    anomalies_df = pd.read_sql_query(query, conn)
    
    if not anomalies_df.empty:
        st.subheader("Risk Breakdown by Account Class")
        class_risk = anomalies_df.groupby("account_class")["risk_score"].mean()
        st.bar_chart(class_risk)
        
        st.subheader("Flagged Anomalies Pipeline")
        
        search = st.text_input("Search Ledger (Entry ID, Posted By, Account Class)...", key="search_ledger")
        if search:
            anomalies_df = anomalies_df[
                anomalies_df['entry_id'].str.contains(search, case=False, na=False) |
                anomalies_df['posted_by'].str.contains(search, case=False, na=False) |
                anomalies_df['account_class'].str.contains(search, case=False, na=False)
            ]
            
        st.dataframe(anomalies_df, use_container_width=True, hide_index=True)
    else:
        st.success("No anomalies detected. The ledger is clean.")

# ----------------- TAB 2: BRAND SENTIMENT -----------------
with tab2:
    st.header("Brand Sentiment Control Center")
    st.caption("Real-time English & Hinglish customer feedback sentiment analytics")
    
    query = """
        SELECT fbr.comment_id, fbr.raw_text, fbr.sentiment_label, fbr.confidence_score, fbr.post_timestamp,
               dsc.platform_name, dsc.author_handle
        FROM fact_brand_reviews fbr
        JOIN dim_sentiment_channels dsc ON fbr.channel_key = dsc.channel_key
        ORDER BY fbr.post_timestamp DESC
    """
    reviews_df = pd.read_sql_query(query, conn)
    
    pos_count = len(reviews_df[reviews_df['sentiment_label'] == 'positive']) if not reviews_df.empty else 0
    neg_count = len(reviews_df[reviews_df['sentiment_label'] == 'negative']) if not reviews_df.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("TOTAL REVIEWS", f"{total_reviews:,}", "Social Scrape Sync")
    col2.metric("POSITIVE REVIEWS", f"{pos_count:,}", "Customer Satisfaction")
    col3.metric("NEGATIVE REVIEWS", f"{neg_count:,}", "Alerts Escalated", delta_color="inverse")
    
    st.markdown("---")
    
    if not reviews_df.empty:
        st.subheader("Scrape Volumes by Social Platform")
        plat_counts = reviews_df['platform_name'].value_counts()
        st.bar_chart(plat_counts)
        
        st.subheader("Brand Feedback Logs")
        
        search_rev = st.text_input("Search Reviews...", key="search_reviews")
        if search_rev:
            reviews_df = reviews_df[
                reviews_df['raw_text'].str.contains(search_rev, case=False, na=False) |
                reviews_df['author_handle'].str.contains(search_rev, case=False, na=False)
            ]
            
        st.dataframe(reviews_df, use_container_width=True, hide_index=True)
    else:
        st.info("No reviews tracked yet.")

# ----------------- TAB 3: MARKET COMPLIANCE -----------------
with tab3:
    st.header("Market Compliance & Pricing Monitor")
    st.caption("Scraped competitor pricing logs tracking dynamic markup violations")
    
    ratio = (total_violations / total_checks * 100) if total_checks > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("TOTAL COMPETITOR CHECKS", f"{total_checks:,}", "Hourly Scraper")
    col2.metric("DECEPTIVE PRICING", f"{total_violations:,}", "Drip Pricing", delta_color="inverse")
    col3.metric("VIOLATION RATIO", f"{ratio:.1f}%", "Target < 5%")

    st.markdown("---")
    
    query = """
        SELECT frp.product_sku, frp.product_name, frp.cart_price, frp.checkout_price,
               frp.price_inflation_pct, frp.is_violation, frp.timestamp,
               dcr.retailer_name
        FROM fact_retail_prices frp
        JOIN dim_competitor_retailers dcr ON frp.retailer_key = dcr.retailer_key
        ORDER BY frp.timestamp DESC
    """
    prices_df = pd.read_sql_query(query, conn)
    
    if not prices_df.empty:
        st.subheader("Drip Pricing Incidents by Merchant (Violations)")
        violations_only = prices_df[prices_df['is_violation'] == 1]
        if not violations_only.empty:
            merch_violations = violations_only['retailer_name'].value_counts()
            st.bar_chart(merch_violations)
        else:
            st.success("No pricing violations detected.")
            
        st.subheader("Competitor Price Audit Feed")
        
        search_price = st.text_input("Search Products/Retailers...", key="search_prices")
        if search_price:
            prices_df = prices_df[
                prices_df['product_name'].str.contains(search_price, case=False, na=False) |
                prices_df['retailer_name'].str.contains(search_price, case=False, na=False)
            ]
            
        st.dataframe(prices_df, use_container_width=True, hide_index=True)
    else:
        st.info("No competitor pricing data available.")

conn.close()
