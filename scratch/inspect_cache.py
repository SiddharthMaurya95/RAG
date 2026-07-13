import sqlite3
import json
import os

db_path = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\data\automotive.db"
if not os.path.exists(db_path):
    print("Database path does not exist:", db_path)
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT query_hash, user_id, expires_at, result_json FROM query_cache;")
rows = cursor.fetchall()
print(f"Total cached queries: {len(rows)}")
for i, row in enumerate(rows):
    qhash, uid, expires, res_json = row
    try:
        data = json.loads(res_json)
        print(f"\n--- Entry {i+1} ---")
        print(f"Hash: {qhash} | User: {uid} | Expires: {expires}")
        print(f"Keys in result: {list(data.keys())}")
        if "type" in data:
            print(f"Type: {data['type']}")
        if "chart_type" in data:
            print(f"Chart Type: {data['chart_type']}")
        if "data" in data:
            d = data["data"]
            if isinstance(d, dict):
                print(f"Data keys: {list(d.keys())}")
                if "df" in d:
                    df_val = d["df"]
                    print(f"df type in json: {type(df_val)}")
                    if isinstance(df_val, dict):
                        print(f"df keys: {list(df_val.keys())}")
            else:
                print(f"Data type: {type(d)}")
    except Exception as e:
        print(f"Error parsing JSON for row {i}: {e}")

conn.close()
