"""
Client app for testing FastAPI LLM server.

Run:
    python app.py
"""

import requests


API_URL = "http://127.0.0.1:8000/query"


payload = {
    "question": "What is vector database?",
    "context": "Vector databases store embeddings for similarity search.",
    "provider": "openai"
}


response = requests.post(API_URL, json=payload)


if response.status_code == 200:

    data = response.json()

    print("\n=== RESPONSE ===")
    print("Provider:", data["provider"])
    print("Model:", data["model"])
    print("Response:\n")
    print(data["response"])

else:
    print("Error:", response.text)