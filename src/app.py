import os
import sqlite3
import csv
import urllib.request
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess

app = FastAPI(
    title="Zenith Corporate Forensic Intelligence Platform",
    description="Backend hosting Zenith's Anomaly Models, local RAG vector engine, and GenAI Auditor Agents.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "zenith.db")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

class ImportRequest(BaseModel):
    url: str

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))

@app.get("/api/v1/summary")
def get_summary_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM fact_journal_entries")
    total_entries = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_audit_log")
    total_audits = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_journal_entries WHERE risk_score > 70")
    flagged_anomalies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_brand_reviews")
    total_reviews = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_retail_prices")
    total_pricing_checks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_retail_prices WHERE is_violation = 1")
    pricing_violations = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_journal_lines": total_entries,
        "total_audited_records": total_audits,
        "flagged_unresolved_anomalies": flagged_anomalies - total_audits if flagged_anomalies > total_audits else 0,
        "total_brand_reviews": total_reviews,
        "total_market_checks": total_pricing_checks,
        "market_violations": pricing_violations
    }

@app.post("/api/v1/ledger/import-url")
def import_ledger_from_url(req: ImportRequest):
    """
    Downloads and imports a financial ledger CSV from an online link or a local file path.
    Maps values and runs the analytics suite automatically.
    """
    url_or_path = req.url.strip()
    print(f"Request to import ledger from: {url_or_path}")
    
    # Resolve file source
    temp_file = os.path.join(BASE_DIR, "db", "temp_import.csv")
    try:
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            # Download file from internet
            print("Downloading online CSV file...")
            urllib.request.urlretrieve(url_or_path, temp_file)
        else:
            # Open local file path directly
            if not os.path.exists(url_or_path):
                raise HTTPException(status_code=400, detail=f"Local file not found at: {url_or_path}")
            temp_file = url_or_path
            
        # Parse CSV and Ingest
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Load dimension mappings to map codes to primary keys
        cursor.execute("SELECT account_key, account_code FROM dim_accounts")
        acct_map = {code: key for key, code in cursor.fetchall()}
        
        cursor.execute("SELECT entity_key, entity_code FROM dim_entities")
        entity_map = {code: key for key, code in cursor.fetchall()}
        
        cursor.execute("SELECT user_key, user_id FROM dim_users")
        user_map = {uid: key for key, uid in cursor.fetchall()}
        
        imported_entries = []
        
        with open(temp_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Map CSV attributes to DB columns
                acct_code = row.get("account_code")
                ent_code = row.get("entity_code")
                user_id = row.get("user_id")
                
                acct_key = acct_map.get(acct_code)
                entity_key = entity_map.get(ent_code)
                user_key = user_map.get(user_id)
                
                if not acct_key or not entity_key or not user_key:
                    # Skip invalid rows or columns
                    continue
                    
                imported_entries.append((
                    row.get("entry_id"),
                    acct_key,
                    entity_key,
                    user_key,
                    row.get("transaction_date"),
                    float(row.get("debit_amount", 0.0)),
                    float(row.get("credit_amount", 0.0)),
                    int(row.get("is_manual_override", 0)),
                    row.get("posted_by"),
                    row.get("approved_by")
                ))
                
        if not imported_entries:
            conn.close()
            raise HTTPException(status_code=400, detail="No valid ledger rows could be parsed from the CSV file.")
            
        # Clear existing transactions and insert new dataset
        cursor.execute("DELETE FROM fact_journal_entries")
        cursor.execute("DELETE FROM fact_audit_log")
        
        cursor.executemany(
            """INSERT INTO fact_journal_entries (
                entry_id, account_key, entity_key, user_key, transaction_date,
                debit_amount, credit_amount, is_manual_override, posted_by, approved_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            imported_entries
        )
        conn.commit()
        conn.close()
        
        print(f"Successfully ingested {len(imported_entries)} ledger rows.")
        
        # Cleanup temporary file if downloaded
        if temp_file == os.path.join(BASE_DIR, "db", "temp_import.csv") and os.path.exists(temp_file):
            os.remove(temp_file)
            
        # Trigger anomaly pipeline execution
        trigger_audit_pipeline()
        
        return {
            "status": "success",
            "message": f"Successfully imported {len(imported_entries)} lines, ran ML anomaly scoring, and generated audits."
        }
        
    except Exception as e:
        if os.path.exists(os.path.join(BASE_DIR, "db", "temp_import.csv")):
            os.remove(os.path.join(BASE_DIR, "db", "temp_import.csv"))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/run")
@app.post("/api/v1/audit/run")
def trigger_audit_pipeline():
    print("Executing Zenith Auditing Pipeline...")
    python_bin = os.path.join(BASE_DIR, "venv", "bin", "python3")
    
    try:
        subprocess.run([python_bin, os.path.join(BASE_DIR, "src", "anomaly_detector.py")], check=True)
        subprocess.run([python_bin, os.path.join(BASE_DIR, "src", "audit_agent.py")], check=True)
        subprocess.run([python_bin, os.path.join(BASE_DIR, "src", "export_data.py")], check=True)
        return {
            "status": "success",
            "message": "Full auditing run completed. Anomaly scores calculated, audits logged, and CSV outputs updated."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/api/v1/audit/anomalies")
def get_anomalies():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT fje.entry_id, fje.transaction_date, fje.posted_by, fje.approved_by, 
               (fje.debit_amount + fje.credit_amount) AS amount, fje.risk_score,
               da.account_name, da.account_class,
               fal.llm_determination, fal.llm_audit_summary
        FROM fact_journal_entries fje
        JOIN dim_accounts da ON fje.account_key = da.account_key
        LEFT JOIN fact_audit_log fal ON fje.entry_id = fal.entry_id
        WHERE fje.risk_score > 70.0
        ORDER BY fje.risk_score DESC
    """
    cursor.execute(query)
    anomalies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"count": len(anomalies), "anomalies": anomalies}

@app.get("/api/v1/brand/reviews")
def get_brand_reviews():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT fbr.comment_id, fbr.raw_text, fbr.sentiment_label, fbr.confidence_score, fbr.post_timestamp,
               dsc.platform_name, dsc.author_handle
        FROM fact_brand_reviews fbr
        JOIN dim_sentiment_channels dsc ON fbr.channel_key = dsc.channel_key
        ORDER BY fbr.post_timestamp DESC
    """
    cursor.execute(query)
    reviews = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"count": len(reviews), "reviews": reviews}

@app.get("/api/v1/market/prices")
def get_market_prices():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT frp.price_key, frp.product_sku, frp.product_name, frp.cart_price, frp.checkout_price,
               frp.price_inflation_pct, frp.is_violation, frp.violation_category, frp.timestamp,
               dcr.retailer_name, dcr.domain_url
        FROM fact_retail_prices frp
        JOIN dim_competitor_retailers dcr ON frp.retailer_key = dcr.retailer_key
        ORDER BY frp.timestamp DESC
    """
    cursor.execute(query)
    prices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"count": len(prices), "prices": prices}

@app.get("/api/v1/audit/explanation/{entry_id}")
def get_anomaly_explanation(entry_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT fje.entry_id, fje.transaction_date, fje.posted_by, fje.approved_by, 
               fje.debit_amount, fje.credit_amount, fje.is_manual_override, fje.risk_score,
               da.account_code, da.account_name, da.account_class,
               de.entity_name, de.country,
               fal.audit_date, fal.llm_determination, fal.llm_audit_summary
        FROM fact_journal_entries fje
        JOIN dim_accounts da ON fje.account_key = da.account_key
        JOIN dim_entities de ON fje.entity_key = de.entity_key
        LEFT JOIN fact_audit_log fal ON fje.entry_id = fal.entry_id
        WHERE fje.entry_id = ?
    """
    cursor.execute(query, (entry_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"Transaction with entry_id '{entry_id}' not found.")
        
    return {
        "entry_id": entry_id,
        "risk_score": rows[0]["risk_score"],
        "entity": f"{rows[0]['entity_name']} ({rows[0]['country']})",
        "posted_by": rows[0]["posted_by"],
        "approved_by": rows[0]["approved_by"],
        "journal_lines": [
            {
                "account_code": r["account_code"],
                "account_name": r["account_name"],
                "account_class": r["account_class"],
                "debit": r["debit_amount"],
                "credit": r["credit_amount"],
                "is_manual_override": r["is_manual_override"]
            } for r in rows
        ],
        "audit_report": {
            "audited_at": rows[0]["audit_date"],
            "determination": rows[0]["llm_determination"],
            "summary": rows[0]["llm_audit_summary"]
        } if rows[0]["llm_determination"] else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
