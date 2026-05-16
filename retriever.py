"""
Retrieval pipeline implementing the full FAQ retrieval algorithm with guardrails.

The algorithm:
1. Vectorize the query
2. Guardrail check - reject if too similar to blocked topics
3. Initial ranking - rank FAQs by cosine similarity to query
4. Similarity collapse filter - remove FAQs too similar to query itself
5. LLM call - format results as context
"""

from typing import Optional
from tree import LeafNode, RoutingTree
from vector_store import VectorStore
import fasttext


class GuardrailException(Exception):
    """Raised when a query violates guardrail constraints."""
    pass


class Retriever:
    """
    Retrieval pipeline that orchestrates:
    - Tree traversal to find the right leaf node
    - Guardrail checking against blocked topics
    - FAQ ranking and filtering
    - Context formatting for LLM
    """

    def __init__(
        self,
        tree: RoutingTree,
        k: int = 5,
        theta_guard: float = 0.85,
        theta_collapse: float = 0.95,
        pick_threshold: float = 0.3,
    ):
        """
        Initialize the retriever with configuration parameters.

        Args:
            tree: RoutingTree instance for query routing
            k: Number of FAQs to retrieve (target count)
            theta_guard: Similarity threshold for guardrail blocking
            theta_collapse: Similarity threshold for collapse filtering
            pick_threshold: Minimum similarity to include an FAQ
        """
        self.tree = tree
        self.k = k
        self.theta_guard = theta_guard
        self.theta_collapse = theta_collapse
        self.pick_threshold = pick_threshold

        # Grab the shared FastText model to prevent memory exhaustion
        self.ft = VectorStore.get_model()

    def retrieve(self, query: str, query_meta: dict) -> list[dict]:
        """
        Full retrieval pipeline: route -> guardrail -> rank -> collapse -> format.

        Args:
            query: The user query string
            query_meta: Metadata for routing (e.g., {"product": "cmaap", "topic": "sql"})

        Returns:
            List of FAQ payloads with similarity scores

        Raises:
            GuardrailException: If query violates guardrail constraints
        """
        # Step 0: Route to appropriate leaf node
        leaf_node = self.tree.traverse(query_meta)

        # Step 1: Vectorize the query
        query_vector = self.ft.get_sentence_vector(query).tolist()

        # Step 2: Guardrail check
        self._check_guardrails(query_vector, leaf_node.guardrail_store)

        # Step 3 & 4: Initial ranking + Collapse filter
        faqs = self._rank_and_filter_faqs(
            query_vector, leaf_node.faq_store, query
        )

        # Step 5: Return top-k results
        return faqs[:self.k]

    def _check_guardrails(self, query_vector: list[float], guardrail_store: VectorStore) -> None:
        """
        Check if query violates guardrail constraints.

        If the query's cosine similarity to any guardrail vector exceeds theta_guard,
        raise GuardrailException.

        Args:
            query_vector: Vectorized query
            guardrail_store: VectorStore containing blocked topics

        Raises:
            GuardrailException: If query is too similar to a guardrail
        """
        if not guardrail_store.vectors:
            return  # No guardrails to check

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
        """
        Rank FAQs by similarity and apply collapse filter.

        Implements:
        - Step 3: Initial ranking by cosine similarity
        - Step 4: Similarity collapse filter to avoid near-duplicates

        Args:
            query_vector: Vectorized query
            faq_store: VectorStore containing FAQs
            query: Original query string (for collapse filtering)

        Returns:
            Filtered and ranked list of FAQ payloads
        """
        if not faq_store.vectors:
            return []

        # Step 3: Compute similarities and rank all FAQs
        faq_rankings = []
        for i, faq_vector in enumerate(faq_store.vectors):
            similarity = VectorStore.cosine_similarity(query_vector, faq_vector)

            # Only consider FAQs above pick_threshold
            if similarity >= self.pick_threshold:
                faq_rankings.append(
                    {
                        "index": i,
                        "similarity": similarity,
                        "payload": faq_store.payloads[i],
                    }
                )

        # Sort by similarity descending
        faq_rankings.sort(key=lambda x: x["similarity"], reverse=True)

        # Step 4: Apply collapse filter
        # Remove FAQs that are too similar to the query itself (near-duplicates)
        filtered_faqs = []
        for faq_info in faq_rankings:
            similarity = faq_info["similarity"]

            # If FAQ is TOO similar to query (likely verbatim or trivial), skip it
            if similarity > self.theta_collapse:
                continue

            # Add to results
            filtered_faq = faq_info["payload"].copy()
            filtered_faq["_similarity_score"] = similarity
            filtered_faqs.append(filtered_faq)

            # Stop once we have k results
            if len(filtered_faqs) >= self.k:
                break

        return filtered_faqs

    @staticmethod
    def format_context(faqs: list[dict]) -> str:
        """
        Format FAQs as context for LLM.

        Args:
            faqs: List of FAQ payloads with metadata

        Returns:
            Formatted context string
        """
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
