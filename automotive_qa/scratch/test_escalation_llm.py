import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import QueryRouter
from core.singletons import get_db_connection, get_llm

db_path = get_db_connection()
router = QueryRouter(db_path)

query = "Generate report for all unresolved repair cases."
res = router.dispatch_query(query, user_id=1)

print("INTENT:", res["intent"])
print("TYPE:", res["type"])
if res["type"] == "table_stream":
    messages = res["data"]["messages"]
    print("MESSAGES SENT TO LLM:")
    for msg in messages:
        print(f"[{msg['role'].upper()}]: {msg['content'][:200]}...")
    
    llm = get_llm()
    print("\n--- GENERATED RESPONSE FROM LLM ---")
    response_text = ""
    for chunk in llm.generate_chat_stream(messages):
        response_text += chunk
        sys.stdout.write(chunk)
        sys.stdout.flush()
    print("\n----------------------------------")
    print("Total Length of Response:", len(response_text))
