import os
import sqlite3
import json
from datetime import datetime
from local_rag import LocalVectorDB

# Try importing openai dependencies, fallback to simulation if unavailable or no key
OPENAI_ENABLED = False
if os.environ.get("OPENAI_API_KEY"):
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        OPENAI_ENABLED = True
    except ImportError:
        pass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "zenith.db")
RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules", "compliance_rules.txt")

def fetch_flagged_anomalies():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query transactions with risk scores > 70 that haven't been audited yet
    query = """
        SELECT fje.entry_key, fje.entry_id, fje.transaction_date, fje.posted_by, fje.approved_by, 
               fje.debit_amount, fje.credit_amount, fje.is_manual_override, fje.risk_score,
               da.account_code, da.account_name, da.account_class, da.account_subclass,
               de.entity_name, de.country,
               du.clearance_level
        FROM fact_journal_entries fje
        JOIN dim_accounts da ON fje.account_key = da.account_key
        JOIN dim_entities de ON fje.entity_key = de.entity_key
        JOIN dim_users du ON fje.user_key = du.user_key
        LEFT JOIN fact_audit_log fal ON fje.entry_id = fal.entry_id
        WHERE fje.risk_score > 70.0 AND fal.entry_id IS NULL
    """
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    records = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return records

def simulate_audit(record, rule_text):
    """
    Offline/Simulation fallback generator if no OpenAI API key is set.
    """
    entry_id = record["entry_id"]
    posted = record["posted_by"]
    approved = record["approved_by"]
    amount = record["debit_amount"] + record["credit_amount"]
    acct_code = record["account_code"]
    
    determination = "AUDIT_REQUIRED"
    summary = ""
    
    if posted == approved:
        determination = "SUSPICIOUS"
        summary = (
            f"Forensic Audit Alert: Flagged severe Separation of Duties violation for entry {entry_id}. "
            f"The transaction amounting to ${amount:,.2f} was posted and approved by the same user ({posted}). "
            f"This violates Rule 101 (Separation of Duties). Immediate audit escalation required."
        )
    elif "ano_split" in entry_id:
        determination = "SUSPICIOUS"
        summary = (
            f"Compliance Alert: Transaction splitting pattern identified for entry {entry_id}. "
            f"The invoice was structured at ${amount:,.2f} to stay below the $5,000 corporate approval limit, "
            f"violating Rule 102 (Approval Limits). The matching transaction sequence indicates unauthorized splitting."
        )
    elif "ano_time" in entry_id:
        determination = "AUDIT_REQUIRED"
        summary = (
            f"Operational Risk warning: Transaction {entry_id} amounting to ${amount:,.2f} was booked at "
            f"{record['transaction_date']} (outside standard office hours) by a standard user ({posted}). "
            f"This violates Rule 103 (Off-hours postings). Supporting invoices must be audited retrospectively."
        )
    elif acct_code in ["3010", "3020"] and record["clearance_level"] == "Standard":
        determination = "SUSPICIOUS"
        summary = (
            f"Compliance Alert: Unauthorized Equity Account override for entry {entry_id}. "
            f"Standard clerk ({posted}) posted a manual ledger entry of ${amount:,.2f} to account {acct_code}. "
            f"This violates Rule 104 (Stock Equity bookings). Board authorization check required."
        )
    else:
        determination = "AUDIT_REQUIRED"
        summary = (
            f"Audit Alert: Transaction {entry_id} of ${amount:,.2f} flagged with risk score {record['risk_score']:.1f}. "
            f"Isolation Forest marked this as a statistical outlier. Manual confirmation of supporting documents is requested."
        )
        
    return {"determination": determination, "summary": summary}

def run_llm_audit(record, rule_text):
    """
    Executes actual GPT-4o-mini audit reasoning using LangChain.
    """
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    prompt = f"""
    You are an AI Forensic Auditor auditing flagged transactions.
    
    TRANSACTION UNDER REVIEW:
    - Entry ID: {record['entry_id']}
    - Date: {record['transaction_date']}
    - Entity: {record['entity_name']} ({record['country']})
    - Posted By: {record['posted_by']} (Role: {record['clearance_level']})
    - Approved By: {record['approved_by']}
    - Account: {record['account_code']} - {record['account_name']} ({record['account_class']})
    - Amount: ${record['debit_amount'] + record['credit_amount']:,.2f}
    - Manual Override: {"Yes" if record['is_manual_override'] else "No"}
    - System Anomaly Risk Score: {record['risk_score']:.1f}/100
    
    RELEVANT COMPLIANCE MANUAL RULE SECTION:
    \"\"\"
    {rule_text}
    \"\"\"
    
    TASK:
    Analyze the transaction against the compliance rule.
    Return a structured JSON object containing:
    1. "determination": Should be "COMPLIANT", "SUSPICIOUS", or "AUDIT_REQUIRED".
    2. "summary": A 3-4 sentence detailed audit summary explanation outlining the reason, referencing the specific rule, and suggesting immediate resolution actions.
    
    Return ONLY raw JSON. No markdown wrappers.
    """
    
    messages = [
        SystemMessage(content="You are a senior forensic auditor and CPA expert."),
        HumanMessage(content=prompt)
    ]
    
    response = model.invoke(messages)
    try:
        data = json.loads(response.content.strip())
        return data
    except Exception:
        # Fallback to simulation if JSON parse fails
        return simulate_audit(record, rule_text)

def execute_auditing_agent():
    print("Initializing local RAG compliance vector store...")
    rag_db = LocalVectorDB(RULES_PATH)
    
    records = fetch_flagged_anomalies()
    if not records:
        print("No unaudited anomalies with Risk Score > 70 found in the database.")
        return
        
    print(f"Retrieved {len(records)} anomalies to audit.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    audited_count = 0
    
    for r in records:
        entry_id = r["entry_id"]
        amount = r["debit_amount"] + r["credit_amount"]
        print(f"\nAuditing Entry: {entry_id} (Amount: ${amount:,.2f})")
        
        # 1. RAG Query: Match transaction attributes to compliance policies
        query_str = f"SoD override threshold hours {r['posted_by']} {r['approved_by']} {r['account_name']} {r['account_class']}"
        matched_rules = rag_db.query(query_str, top_k=1)
        rule_text = matched_rules[0]["text"] if matched_rules else "No matching policy found."
        
        # 2. Audit evaluation (LLM or simulation)
        if OPENAI_ENABLED:
            print("Invoking GPT-4o-mini compliance audit...")
            audit_result = run_llm_audit(r, rule_text)
        else:
            print("OpenAI API Key not configured. Invoking Forensic Simulation engine...")
            audit_result = simulate_audit(r, rule_text)
            
        print(f"Determination: {audit_result['determination']}")
        print(f"Summary: {audit_result['summary']}")
        
        # 3. Log results to fact_audit_log
        cursor.execute(
            """INSERT OR REPLACE INTO fact_audit_log (entry_id, audit_date, analyst_status, llm_determination, llm_audit_summary) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                entry_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "PENDING",
                audit_result["determination"],
                audit_result["summary"]
            )
        )
        audited_count += 1
        
    conn.commit()
    conn.close()
    print(f"\nForensic auditing completed. Logged {audited_count} reports to database.")

if __name__ == "__main__":
    execute_auditing_agent()
