# Objective: Temporary scratchpad for sanity-checking components and LLM/pipeline functionality.
import sys
import os

sys.path.append(os.path.abspath("."))

from core.router import QueryRouter

# Location: automotive_qa/scratch_test.py

# Ensure we can import from core and analytics

def main():
    router = QueryRouter()
    
    test_queries = [
        "Find FTIR reports about engine failures in USA",
        "Show me the top 5 dealers by failure count",
        "What is the trend of monthly failures for model XC90?",
        "Compare the failure rates between product model XC90 and S60",
        "What is the distribution of using mileage before failure?",
        "Generate the monthly QA report for May 2024",
        "Show me the distribution of quality ratings",
        "What is the overall repair success rate?",
        "What are the most common failed parts?"
    ]
    
    print("Starting query validation test...\n")
    
    for i, q in enumerate(test_queries, 1):
        print(f"--- Test Query {i} ---")
        print(f"Q: '{q}'")
        try:
            res = router.dispatch_query(q, user_id=999)
            print(f"Intent: {res.get('intent')}")
            print(f"Type: {res.get('type')}")
            
            if res.get('type') == 'table_stream' or res.get('type') == 'table_only':
                df = res['data'].get('df', None) if isinstance(res['data'], dict) else res['data']
                if df is not None and not df.empty:
                    print(f"Data shape: {df.shape}")
                    print(f"Chart Type: {res.get('chart_type')}")
                    print(f"SQL Used: {res.get('sql_query')}")
                else:
                    print("Data: EMPTY")
            elif res.get('type') == 'text_stream':
                print(f"Data (messages count): {len(res.get('data', []))}")
                if res.get('citations'):
                    print(f"Citations found: {len(res['citations'])}")
            elif res.get('type') == 'report':
                print(f"Report Data: {res.get('data')}")
                
        except Exception as e:
            print(f"ERROR executing query: {e}")
        print("\n")

if __name__ == "__main__":
    main()
