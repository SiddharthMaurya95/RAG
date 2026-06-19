import sys
import os

# Append automotive_qa to path
sys.path.append(os.path.join(os.path.abspath("."), "automotive_qa"))

from core.router import QueryRouter
from nlp.pipeline import NLPProcessor

router = QueryRouter()
nlp = NLPProcessor()

# Test 1: Extract entities
queries = [
    "tell me about FTIR UY202606B00007",
    "what is FTIR AE202406B01074?",
    "what is FTIR/2024/1018?",
    "explain FTIR No. UY202606B99999"
]

print("--- ENTITY EXTRACTION TEST ---")
for q in queries:
    res = nlp.parse_query(q)
    print(f"Query: {q}")
    print(f"Entities: {res['entities']}")
    print(f"Intent: {res['intent']}")
    print("-" * 30)

print("\n--- ROUTING AND SEARCH TEST ---")
for q in queries:
    res = router.dispatch_query(q)
    print(f"Query: {q}")
    print(f"Intent: {res['intent']}")
    print(f"Type: {res['type']}")
    print(f"Citations: {res['citations']}")
    # If messages are returned, print the system prompt and prompt
    if res['type'] == 'text_stream':
        messages = res['data']
        for msg in messages:
            print(f"Role [{msg['role']}]: {msg['content'][:200]}...")
    print("=" * 40)
