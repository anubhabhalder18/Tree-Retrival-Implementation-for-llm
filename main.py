import requests
import json


BASE_URL = "http://127.0.0.1:8000"


# =========================================================
# HELPERS
# =========================================================

def pretty_print(title, data):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(json.dumps(data, indent=2))


# =========================================================
# ROOT TEST
# =========================================================

print("\nChecking server...\n")

r = requests.get(f"{BASE_URL}/")

pretty_print("ROOT RESPONSE", r.json())


# =========================================================
# TREE RELOAD
# =========================================================

print("\nReloading tree...\n")

r = requests.post(f"{BASE_URL}/tree_reload")

pretty_print("TREE RELOAD RESPONSE", r.json())


# =========================================================
# QUERY 1
# =========================================================

query_1 = {
    "query": "How do I convert SQL Server CAST functions?",
    "query_meta": {
        "product": "cmaap",
        "topic": "sql-migration",
        "dialect": "tsql"
    },
    "k": 3
}

r = requests.post(
    f"{BASE_URL}/query",
    json=query_1
)

pretty_print("QUERY 1 RESPONSE", r.json())


# =========================================================
# QUERY 2
# =========================================================

query_2 = {
    "query": "How do I migrate SSIS packages?",
    "query_meta": {
        "product": "cmaap",
        "topic": "ssis-migration"
    },
    "k": 2
}

r = requests.post(
    f"{BASE_URL}/query",
    json=query_2
)

pretty_print("QUERY 2 RESPONSE", r.json())


# =========================================================
# QUERY 3
# =========================================================

query_3 = {
    "query": "What databases does CMaaP support?",
    "query_meta": {
        "product": "cmaap"
    },
    "k": 2
}

r = requests.post(
    f"{BASE_URL}/query",
    json=query_3
)

pretty_print("QUERY 3 RESPONSE", r.json())


# =========================================================
# ADD LEAF NODE
# =========================================================

leaf_node = {
    "metadata": {
        "product": "cmaap",
        "topic": "snowflake-migration"
    },
    "faq_store_name": "snowflake_faq",
    "guardrail_store_name": "snowflake_guardrail"
}

r = requests.post(
    f"{BASE_URL}/put_leafnode",
    json=leaf_node
)

pretty_print("PUT LEAFNODE RESPONSE", r.json())


print("\nDemo completed.\n")