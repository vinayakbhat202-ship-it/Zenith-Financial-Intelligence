import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.express as px

# Page Config
st.set_page_config(
    page_title="Zenith Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced Custom CSS for a Premium Dark Aesthetic (similar to previous UI)
st.markdown("""
<style>
    /* Main Background Gradient */
    .stApp {
        background: linear-gradient(135deg, #090916 0%, #15112e 100%);
        color: #e2e8f0;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: rgba(13, 11, 33, 0.7);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #c7d2fe !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Metric Cards */
    [data-testid="metric-container"] {
        background: rgba(20, 20, 40, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Metric Value */
    [data-testid="stMetricValue"] {
        color: #818cf8 !important;
        font-weight: 700;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: rgba(255,255,255,0.05);
        border-radius: 10px 10px 0px 0px;
        color: #a5b4fc;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(180deg, rgba(99, 102, 241, 0.2) 0%, transparent 100%);
        border-bottom: 2px solid #6366f1;
        color: #ffffff;
    }
    
    /* Inputs / Buttons */
    .stTextInput input {
        background-color: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 8px !important;
        color: white !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        border: none;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        color: white;
    }
    
    /* Dataframe background */
    [data-testid="stDataFrame"] {
        background-color: rgba(255,255,255,0.02);
        border-radius: 10px;
        padding: 10px;
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
        class_risk = anomalies_df.groupby("account_class")["risk_score"].mean().reset_index()
        fig_risk = px.bar(class_risk, x="risk_score", y="account_class", orientation='h', 
                          color="risk_score", color_continuous_scale="Purples",
                          title="Average Risk Score by Account Class")
        fig_risk.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig_risk, use_container_width=True)
        
        st.subheader("Flagged Anomalies Pipeline")
        
        search = st.text_input("Search Ledger (Entry ID, Posted By, Account Class)...", key="search_ledger")
        if search:
            anomalies_df = anomalies_df[
                anomalies_df['entry_id'].str.contains(search, case=False, na=False) |
                anomalies_df['posted_by'].str.contains(search, case=False, na=False) |
                anomalies_df['account_class'].str.contains(search, case=False, na=False)
            ]
            
        # Format columns for display
        display_df = anomalies_df.rename(columns={
            "entry_id": "Entry ID",
            "transaction_date": "Date",
            "posted_by": "Posted By",
            "amount": "Amount ($)",
            "risk_score": "Risk Score",
            "account_class": "Account Class",
            "llm_determination": "AI Audit Status",
            "llm_audit_summary": "Audit Summary"
        })
        display_df['Amount ($)'] = display_df['Amount ($)'].map('{:,.2f}'.format)
        display_df['Risk Score'] = display_df['Risk Score'].map('{:.1f}%'.format)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
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
        plat_counts = reviews_df['platform_name'].value_counts().reset_index()
        plat_counts.columns = ['Platform', 'Count']
        fig_plat = px.pie(plat_counts, values='Count', names='Platform', hole=0.4, 
                          color_discrete_sequence=px.colors.sequential.Purples_r,
                          title="Reviews by Platform")
        fig_plat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig_plat, use_container_width=True)
        
        st.subheader("Brand Feedback Logs")
        
        search_rev = st.text_input("Search Reviews...", key="search_reviews")
        if search_rev:
            reviews_df = reviews_df[
                reviews_df['raw_text'].str.contains(search_rev, case=False, na=False) |
                reviews_df['author_handle'].str.contains(search_rev, case=False, na=False)
            ]
            
        display_rev = reviews_df.rename(columns={
            "comment_id": "Comment ID",
            "raw_text": "Review Text",
            "sentiment_label": "Sentiment",
            "confidence_score": "Confidence",
            "post_timestamp": "Timestamp",
            "platform_name": "Platform",
            "author_handle": "User Handle"
        })
        display_rev['Confidence'] = (display_rev['Confidence'] * 100).map('{:.1f}%'.format)
        
        st.dataframe(display_rev, use_container_width=True, hide_index=True)
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
        st.subheader("Drip Pricing Incidents by Merchant")
        violations_only = prices_df[prices_df['is_violation'] == 1]
        if not violations_only.empty:
            merch_violations = violations_only['retailer_name'].value_counts().reset_index()
            merch_violations.columns = ['Retailer', 'Violations']
            fig_merch = px.pie(merch_violations, values='Violations', names='Retailer', hole=0.4,
                               color_discrete_sequence=px.colors.sequential.Sunset,
                               title="Violations by Retailer")
            fig_merch.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig_merch, use_container_width=True)
        else:
            st.success("No pricing violations detected.")
            
        st.subheader("Competitor Price Audit Feed")
        
        search_price = st.text_input("Search Products/Retailers...", key="search_prices")
        if search_price:
            prices_df = prices_df[
                prices_df['product_name'].str.contains(search_price, case=False, na=False) |
                prices_df['retailer_name'].str.contains(search_price, case=False, na=False)
            ]
            
        display_prices = prices_df.rename(columns={
            "product_sku": "SKU",
            "product_name": "Product Name",
            "cart_price": "Cart Price ($)",
            "checkout_price": "Checkout Price ($)",
            "price_inflation_pct": "Inflation (%)",
            "is_violation": "Violation?",
            "timestamp": "Timestamp",
            "retailer_name": "Retailer"
        })
        display_prices['Cart Price ($)'] = display_prices['Cart Price ($)'].map('{:,.2f}'.format)
        display_prices['Checkout Price ($)'] = display_prices['Checkout Price ($)'].map('{:,.2f}'.format)
        display_prices['Inflation (%)'] = display_prices['Inflation (%)'].map('{:.1f}%'.format)
        display_prices['Violation?'] = display_prices['Violation?'].apply(lambda x: '🚨 Yes' if x == 1 else '✅ No')
        
        st.dataframe(display_prices, use_container_width=True, hide_index=True)
    else:
        st.info("No competitor pricing data available.")

conn.close()
