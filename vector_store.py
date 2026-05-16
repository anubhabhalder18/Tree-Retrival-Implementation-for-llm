import math
import json
import os
import fasttext
import fasttext.util

class VectorStore:
    # Class-level attribute to hold the model once across all instances
    _ft_model = None 

    @classmethod
    def get_model(cls):
        """Loads the fasttext model only if it hasn't been loaded yet."""
        if cls._ft_model is None:
            print("Loading FastText model (this will take a moment)...")
            fasttext.util.download_model('en', if_exists='ignore')
            cls._ft_model = fasttext.load_model('cc.en.300.bin')
        return cls._ft_model

    def __init__(self, name: str):
        self.name = name
        
        # All instances now share the exact same loaded model
        self.ft = self.get_model()
        
        self.vectors: list[list[float]] = []
        self.payloads: list[dict] = []

    def add(self, text: str, payload: dict) -> None:
        """Vectorize text and store with payload."""
        
        vector = self.ft.get_sentence_vector(text).tolist()
      
        enriched_payload = payload.copy()
        if "text" not in enriched_payload:
            enriched_payload["text"] = text
            
        self.vectors.append(vector)
        self.payloads.append(enriched_payload)

    def query(self, text: str, k: int) -> list[dict]:
        """Return top-k results sorted by cosine similarity desc."""
        if not self.vectors:
            return []

        qvec = self.ft.get_sentence_vector(text).tolist()
        
        # Calculate similarity against all stored vectors
        results = []
        for i, vec in enumerate(self.vectors):
            sim = self.cosine_similarity(qvec, vec)
            results.append((sim, self.payloads[i]))
       
        results.sort(key=lambda x: x[0], reverse=True)
       
        top_k_results = []
        for score, payload in results[:k]:
            result_dict = payload.copy()
            result_dict["_similarity_score"] = score
            top_k_results.append(result_dict)
            
        return top_k_results

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """
        Calculates cosine similarity from scratch.
        Formula: (A dot B) / (||A|| * ||B||)
        """
        if len(a) != len(b):
            raise ValueError(f"Vector dimensions mismatch: {len(a)} vs {len(b)}")
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        
        # Edge Case: Handle zero vectors to prevent ZeroDivisionError
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
            
        # Edge Case: Clamp floating point inaccuracies that might slightly exceed 1.0 or -1.0
        similarity = dot_product / (norm_a * norm_b)
        return max(-1.0, min(1.0, similarity))

    # ==========================================
    # Persistence Methods (Pickle-Free)
    # ==========================================

    def save(self, directory: str = "./data") -> None:
        """Serializes the vector store to disk using JSON."""
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, f"{self.name}_store.json")
        
        data = {
            "name": self.name,
            "vectors": self.vectors,
            "payloads": self.payloads
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
    def load(self, directory: str = "./data") -> None:
        """Deserializes the vector store from disk."""
        filepath = os.path.join(directory, f"{self.name}_store.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No saved store found at {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.name = data["name"]
        self.vectors = data["vectors"]
        self.payloads = data["payloads"]