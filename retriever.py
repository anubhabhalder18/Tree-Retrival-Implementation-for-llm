
from typing import Optional
from tree import LeafNode, RoutingTree
from vector_store import VectorStore
import fasttext
class GuardrailException(Exception):
    pass
class Retriever:
    def __init__(
        self,
        tree: RoutingTree,
        k: int = 5,
        theta_guard: float = 0.85,
        theta_collapse: float = 0.95,
        pick_threshold: float = 0.3,
    ):
        self.tree = tree
        self.k = k
        self.theta_guard = theta_guard
        self.theta_collapse = theta_collapse
        self.pick_threshold = pick_threshold
        self.ft = VectorStore.get_model()
    def retrieve(self, query: str, query_meta: dict) -> list[dict]:
        leaf_node = self.tree.traverse(query_meta)
        query_vector = self.ft.get_sentence_vector(query).tolist()
        self._check_guardrails(query_vector, leaf_node.guardrail_store)
        faqs = self._rank_and_filter_faqs(
            query_vector, leaf_node.faq_store, query
        )
        return faqs[:self.k]
    def _check_guardrails(self, query_vector: list[float], guardrail_store: VectorStore) -> None:
        if not guardrail_store.vectors:
            return
        for guardrail_vector in guardrail_store.vectors:
            similarity = VectorStore.cosine_similarity(query_vector, guardrail_vector)
            if similarity > self.theta_guard:
                raise GuardrailException(
                    f"Query violates guardrail constraints (similarity: {similarity:.3f} > {self.theta_guard}). "
                    "This topic is out of scope."
                )
    def _rank_and_filter_faqs(
        self,
        query_vector: list[float],
        faq_store: VectorStore,
        query: str,
    ) -> list[dict]:
        if not faq_store.vectors:
            return []
        faq_rankings = []
        for i, faq_vector in enumerate(faq_store.vectors):
            similarity = VectorStore.cosine_similarity(query_vector, faq_vector)
            if similarity >= self.pick_threshold:
                faq_rankings.append(
                    {
                        "index": i,
                        "similarity": similarity,
                        "payload": faq_store.payloads[i],
                    }
                )
        faq_rankings.sort(key=lambda x: x["similarity"], reverse=True)
        filtered_faqs = []
        for faq_info in faq_rankings:
            similarity = faq_info["similarity"]
            if similarity > self.theta_collapse:
                continue
            filtered_faq = faq_info["payload"].copy()
            filtered_faq["_similarity_score"] = similarity
            filtered_faqs.append(filtered_faq)
            if len(filtered_faqs) >= self.k:
                break
        return filtered_faqs
    @staticmethod
    def format_context(faqs: list[dict]) -> str:
        if not faqs:
            return "No relevant FAQs found."
        context_lines = ["Retrieved FAQ Context:\n"]
        for i, faq in enumerate(faqs, 1):
            similarity = faq.get("_similarity_score", 0.0)
            question = faq.get("question", "N/A")
            answer = faq.get("answer", "N/A")
            context_lines.append(f"FAQ {i} (similarity: {similarity:.3f})")
            context_lines.append(f"Q: {question}")
            context_lines.append(f"A: {answer}\n")
        return "\n".join(context_lines)
