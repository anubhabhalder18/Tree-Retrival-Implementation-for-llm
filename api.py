import requests
import json
import time

API_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")

def run_api_demo():
    print("Starting Tree retrival system...\n")
    
    # Wait for API to be ready
    try:
        requests.get(f"{API_URL}/")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Make sure you run 'python api.py' first.")
        return

    # ---------------------------------------------------------
    # 1. Build the Tree
    # ---------------------------------------------------------
    print_section("1. BUILDING THE TREE (/tree/build)")
    response = requests.post(f"{API_URL}/tree/build")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    # ---------------------------------------------------------
    # 2. Get Tree Definitions
    # ---------------------------------------------------------
    print_section("2. FETCHING TREE DEFINITIONS (/tree)")
    response = requests.get(f"{API_URL}/tree")
    print("Successfully retrieved tree architecture.")
    # Printing just the root keys to avoid flooding the console
    print(json.dumps(response.json()['tree']['metadata'], indent=2))

    # ---------------------------------------------------------
    # 3. Add a Custom Leaf Node
    # ---------------------------------------------------------
    print_section("3. ADDING A NEW LEAF NODE (/tree/leaf)")
    new_leaf_payload = {
        "metadata": {"product": "cmaap", "topic": "oracle-migration", "dialect": "plsql"},
        "faqs": [
            {
                "question": "How do I migrate Oracle Sequences?",
                "answer": "Map Oracle sequences to IDENTITY columns or standard SQL sequences depending on the target."
            }
        ],
        "guardrails": [
            {
                "phrase": "drop tablespace",
                "blocked_reason": "Destructive infrastructure operation"
            }
        ]
    }
    response = requests.post(f"{API_URL}/tree/leaf", json=new_leaf_payload)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    # ---------------------------------------------------------
    # 4. Run Sample Queries
    # ---------------------------------------------------------
    print_section("4. RUNNING QUERIES (/query)")
    
    queries = [
        {
            "query": "How do I convert SQL Server CAST functions to be compatible with Teradata?",
            "meta": {"product": "cmaap", "topic": "sql-migration", "dialect": "tsql"},
            "description": "T-SQL specific query - routes to T-SQL leaf",
        },
        {
            "query": "How do I migrate Oracle Sequences?",
            "meta": {"product": "cmaap", "topic": "oracle-migration", "dialect": "plsql"},
            "description": "Custom PL/SQL query - routes to the newly added leaf",
        },
        {
            "query": "Can you drop tablespace for me?",
            "meta": {"product": "cmaap", "topic": "oracle-migration", "dialect": "plsql"},
            "description": "Triggering the custom guardrail added via API",
        }
    ]

    for i, q in enumerate(queries, 1):
        print(f"\n--- Query {i}: {q['description']} ---")
        print(f"Q: {q['query']}")
        
        response = requests.post(
            f"{API_URL}/query", 
            json={"query": q["query"], "meta": q["meta"]}
        )
        
        result = response.json()
        
        if result["status"] == "success":
            print(f"Context formatted successfully.")
            print("LLM Response:")
            print(result["response"])
        elif result["status"] == "blocked":
            print(f"Guardrail Triggered: {result['reason']}")

    print_section("Demo Completed Successfully")

if __name__ == "__main__":
    run_api_demo()
