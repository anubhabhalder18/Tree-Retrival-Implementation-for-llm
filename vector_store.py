import math
import json
import os
import fasttext
import fasttext.util
class VectorStore:
    _ft_model = None
    @classmethod
    def get_model(cls):
        if cls._ft_model is None:
            print("Loading FastText model (this will take a moment)...")
            fasttext.util.download_model('en', if_exists='ignore')
            cls._ft_model = fasttext.load_model('cc.en.300.bin')
        return cls._ft_model
    def __init__(self, name: str):
        self.name = name
        self.ft = self.get_model()
        self.vectors: list[list[float]] = []
        self.payloads: list[dict] = []
    def add(self, text: str, payload: dict) -> None:
        vector = self.ft.get_sentence_vector(text).tolist()
        enriched_payload = payload.copy()
        if "text" not in enriched_payload:
            enriched_payload["text"] = text
        self.vectors.append(vector)
        self.payloads.append(enriched_payload)
    def query(self, text: str, k: int) -> list[dict]:
        if not self.vectors:
            return []
        qvec = self.ft.get_sentence_vector(text).tolist()
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
        if len(a) != len(b):
            raise ValueError(f"Vector dimensions mismatch: {len(a)} vs {len(b)}")
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        similarity = dot_product / (norm_a * norm_b)
        return max(-1.0, min(1.0, similarity))
    def save(self, directory: str = "./data") -> None:
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
        filepath = os.path.join(directory, f"{self.name}_store.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No saved store found at {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.name = data["name"]
        self.vectors = data["vectors"]
        self.payloads = data["payloads"]
