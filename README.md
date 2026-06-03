---
title: Zenith Forensic Audit System
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Zenith — Enterprise Intelligence Command Center

**Zenith** is a smart digital dashboard that acts as an automated, AI-powered corporate watchdog. In large companies, human auditors can only manually check about 5% of financial transactions for fraud or rule-breaking. Zenith automates this, checking 100% of transactions in real-time.

## 🛠️ Tech Stack Used

*   **Frontend/Backend:** Pure Python via Streamlit
*   **Database:** SQLite (Relational Database)
*   **Machine Learning:** Scikit-Learn (Isolation Forest), Pandas, NumPy
*   **Generative AI / RAG:** LangChain, OpenAI (GPT-4o-mini), ChromaDB (Vector Database)
*   **Deployment:** Docker, Hugging Face Spaces, GitHub

## 🧠 How it Works (Under the Hood)

Zenith uses a dual-engine approach combining traditional statistical Machine Learning with modern Generative AI to ensure zero hallucinations:

1. **Data Ingestion:** Financial ledgers (CSV files) are uploaded and saved into a local SQLite database.
2. **Statistical ML Scan:** `Benford's Law` scans the numbers to see if amounts look human-fabricated, and an `Isolation Forest` model looks for weird patterns (like someone making a huge transaction at 3 AM).
3. **Risk Scoring:** The system assigns every transaction a Risk Score (0-100%). Anything scoring over 70% is flagged.
4. **Context Retrieval (RAG):** For flagged transactions, the system searches `ChromaDB` (which contains the company's secret compliance rulebook) to find the exact corporate rule that might have been broken.
5. **AI Determination:** The flagged transaction + the exact rule are sent to the LLM (`GPT-4o-mini`). 
6. **Final Audit:** The LLM generates a precise forensic summary labeling the transaction as *Compliant*, *Suspicious*, or *Audit Required* using **only** the retrieved context—meaning zero hallucination.

## 🚀 Live Demo

Check out the live interactive dashboard here:  
**[Zenith Audit System Live on Hugging Face Spaces](https://huggingface.co/spaces/vinny2005/zenith-audit-system)**
