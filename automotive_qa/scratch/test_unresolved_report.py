import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import QueryRouter
from core.singletons import get_db_connection

db_path = get_db_connection()
router = QueryRouter(db_path)

query = "Generate report for all unresolved repair cases."
res = router.dispatch_query(query, user_id=1)

print("INTENT:", res["intent"])
print("TYPE:", res["type"])
if res["type"] == "table_stream":
    print("DF shape:", res["data"]["df"].shape)
    print("DF columns:", res["data"]["df"].columns.tolist())
    print("SQL query used:", res.get("sql_query"))
elif res["type"] == "text_stream":
    print("TEXT:", res["data"])
else:
    print("DATA:", res["data"])
