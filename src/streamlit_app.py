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

st.sidebar.markdown(f"**Platform Status:** Active 🟢")
st.sidebar.markdown("---")
st.sidebar.markdown("### System Health")
st.sidebar.markdown(f"- **Journal Lines Processed:** {total_entries:,}")
st.sidebar.markdown(f"- **AI Audits Logged:** {total_audits:,}")
st.sidebar.markdown(f"- **Unresolved Anomalies:** {unresolved:,}")

# Main Layout: Single Page (No Tabs)
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
        
    # Format columns for display natively
    display_df = anomalies_df.rename(columns={
        "entry_id": "Entry ID",
        "transaction_date": "Date",
        "posted_by": "Posted By",
        "amount": "Amount",
        "risk_score": "Risk Score",
        "account_class": "Account Class",
        "llm_determination": "AI Status",
        "llm_audit_summary": "Audit Summary"
    })
    
    # Prettify 'Posted By'
    display_df["Posted By"] = display_df["Posted By"].str.replace("usr_", "").str.title()
    
    # Format AI Status with emojis
    def format_status(x):
        if x == "AUDIT_REQUIRED": return "🚨 REQUIRED"
        if x == "SUSPICIOUS": return "⚠️ SUSPICIOUS"
        if pd.isna(x): return "⏳ PENDING"
        return f"✅ {x}"
    display_df["AI Status"] = display_df["AI Status"].apply(format_status)
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Entry ID": st.column_config.TextColumn("Entry ID", width="small"),
            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "Risk Score": st.column_config.ProgressColumn("Risk Score", format="%.1f%%", min_value=0, max_value=100),
            "Audit Summary": st.column_config.TextColumn("Audit Summary", width="large")
        }
    )
else:
    st.success("No anomalies detected. The ledger is clean.")

conn.close()
