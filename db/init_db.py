import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "zenith.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def initialize_database():
    print(f"Initializing Zenith SQLite Database at: {DB_PATH}")
    
    # Establish connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
        
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("Database schema applied successfully.")
    except Exception as e:
        print(f"Error applying schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database()
