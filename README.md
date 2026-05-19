# Design Document: Tree-Structured Vector Retrieval System

## Overview

This document details the design decisions, complexity analysis, and scaling strategies for a hierarchical vector retrieval system built using first principle. The system combines metadata-aware tree routing with dual vector stores (FAQ and guardrails) at leaf nodes to provide accurate, scoped, and safe response generation.

FLOW OF WORKFLOW while making a query-

Tree is queried -> Query goes through a domain partinized Tree -> Exact leafnode with matching metadata is selected -> The query is checked conisne similarity with FAQs the first k FAQS are passed to llm (exception if query matches GAURDRAIL it is terminated)

<img width="664" height="873" alt="image" src="https://github.com/user-attachments/assets/7929956f-bc86-42e3-8673-a2ea8f18c3e3" />


---

## 1. Complexity Analysis

### Time Complexity: End-to-End Query Processing

Breaking down each phase:

#### Phase 1: Tree Traversal — O(T * D)

- **T** = depth of tree (typically 2-5 for domain partitioning)
- At each level, we match query metadata against children: O(C) where C = branching factor
- **Path search**: O(T·C) in worst case (all children checked), but typically O(T) with early termination
- **Conclusion**: O(T) or O(T·C) depending on branching strategy; negligible for typical trees

#### Phase 2: Guardrail Check — O(G·D)

- **G** = number of guardrail vectors
- **D** = vector dimension (300 for fasttext)
- Each cosine similarity: O(D) dot product + O(D) norm calculations = O(D)
- Check all guardrails: O(G·D)
- **Typical**: G is small (5-50), so ~1.5-15K operations

#### Phase 3: Initial Ranking (FAQ Scoring) — O(F·D)

- **F** = number of FAQs in leaf store
- Calculate similarity for all FAQs: O(F·D)
- Sort by similarity: O(F·log F) (merge sort)
- **Total ranking**: O(F·D + F·log F) ≈ **O(F·D)** (since D >> log F typically)

#### Phase 4: Collapse Filter — O(k)

- Iterate through top-k candidates after sorting
- Each comparison is O(1) similarity check (already computed)
- **Total**: O(k) where k ≤ min(F, requested k)

#### Phase 5: LLM Context Formatting — O(k·text_length)

- Format k FAQs with question/answer text
- Negligible compared to vector operations

**Final Time Complexity:**

```
O(T) + O(G·D) + O(F·D + F·log F) + O(k)
≈ O(max(G·D, F·D))
≈ O(D·(G + F))
```

For typical parameters:

- D = 300 (fasttext)
- G = 20 (guardrails per leaf)
- F = 1,000 (FAQs per leaf)
- **Total**: ~315K operations per query (~5-10ms on modern hardware)

### Space Complexity

**Overall: O(N·D + F_total·D) = O(D·(N + F_total))**

#### Tree Structure: O(N·M)

- **N** = number of tree nodes (internal + leaf)
- **M** = average metadata size per node (small, ~10-100 bytes)
- Tree structure itself is sparse: O(N·M) << vector data

#### Vector Stores: O((F + G)·D) per leaf

- **F** = FAQs per leaf node
- **G** = guardrails per leaf node
- **D** = vector dimension (300)
- **Per leaf**: (F + G) vectors of dimension D
  - Example: (1,000 + 20) × 300 = 306K floats ≈ 1.2 MB per leaf

#### Total with 10,000 Leaf Nodes:

```
N = 10,000 leaves (plus internal nodes)
F_total = 10,000 × 50,000 = 500M vectors
Memory = 500M × 300 × 4 bytes (float32) ≈ 600 GB

Key insight: Vector storage dominates tree overhead.
```

### Bottleneck Analysis

**Primary bottleneck: FAQ vector scoring — O(F·D)**

Under load, the FAQ ranking phase consumes the most CPU:

- Linear scan through F vectors
- 300 dimensions of FLOPs per vector
- No caching (vectors differ per query)

**Secondary bottleneck: Guardrail checking**

- Happens before FAQ scoring (good for early rejection)
- O(G·D) is usually small (G ≤ 50)

**Memory bottleneck at scale**

- 600 GB for 10K leaves × 50K FAQs (uncompressed float32)
- Requires ANN indexing or quantization strategies

**Profiling recommendations:**

1. **Fast path**: Guardrail check cost vs. savings from early termination
2. **Hot path**: FAQ ranking (profile vector operations and sorting)
3. **Memory**: Monitor per-leaf vector store growth
4. **Query load**: Measure concurrent request handling and context switch costs

---

## 2. Scaling Proposal

### Challenge: 10,000 Leaf Nodes × 50,000 FAQs × 1,000 QPS × Multi-tenant Isolation

#### A. Sharding Strategy

**Tenant-based sharding** (primary dimension):

```
Shard = hash(tenant_id) % num_shards
Each shard holds:
  - Customer-exclusive tree partition
  - All leaf nodes for that tenant
  - All FAQ/guardrail vectors
```

**Benefits:**

- Hard multi-tenant isolation (no cross-customer data leakage)
- Horizontal scaling: add shards as tenant base grows
- Predictable resource allocation per tenant

**Implementation:**

```
shards: {
  shard_0: {tenants: [cust_a, cust_b], nodes: 500, faqs: 25M},
  shard_1: {tenants: [cust_c], nodes: 300, faqs: 15M},
  ...
}
```

#### B. Approximate Nearest Neighbor (ANN) Indexing

**Replace linear scan O(F·D) with ANN lookup O(log F)**

**We can approach:**

1. **HNSW (Hierarchical Navigable Small World)**

   - Build: O(F·D·log F)
   - Query: O(log F·D) for ~100 nearest neighbors
   - Memory: ~20% overhead vs. flat vectors
   - **Best for**: High-recall retrieval (match quality priority)
2. **IVF (Inverted File with Product Quantization)**

   - Build: O(F·D·k) where k = num clusters
   - Query: O(k·D + probe_lists·D)
   - Memory: O(F·d') where d' << D (compressed)
   - **Best for**: Memory-constrained scenarios
3. **LSH (Locality Sensitive Hashing)**

   - Build: O(F)
   - Query: O(hash_tables)
   - Memory: Minimal
   - **Trade-off**: Lower accuracy, but extremely fast

**Recommendation for The system:**

```
I will be using  HNSW because:
  - FAQ quality (recall) is paramount
  - Queries are sequential, not massively parallel
  - User expects correct answers first
  - Can afford 10-50ms per query
```

**Complexity reduction:**

```
Current:     O(F·D) + O(F·log F) ≈ O(300·50K) = 15M ops
HNSW:        O(log F·D)         ≈ O(16·300) = 4.8K ops
Speedup:     ~3000x faster
```

#### C. Caching Strategy

**Multi-level cache:**

1. **Query Result Cache** (most effective)

   ```
   Key: (tenant_id, query_hash, k)
   Value: [faq_ids, similarity_scores]
   TTL: 1 hour
   Expected hit rate: 30-40% (repeated queries)
   ```
2. **Vector Cache** (in-process LRU)

   ```
   Cache frequently accessed leaf nodes' FAQ vectors in RAM
   Evict LRU when memory threshold hit
   Typically 20-30 hot leaves cached
   ```
3. **Guardrail Cache** (aggressive)

   ```
   Guardrail checks are expensive but results are stable
   Cache guardrail embeddings + rejection status
   Cache hit rate: 70-80% (much smaller set)
   ```

**Estimated impact:**

```
- Query cache hit saves 80% latency
- Guardrail cache hit saves 10% latency
- Vector prefetching saves 5-10% latency
- Combined: 35-40% latency reduction at 40% hit rate
```

#### D. Concurrency & Load Handling

**For 1,000 QPS:**

```
Single machine (CPU-bound):
  - FAQ scoring: 50K vectors × 300 dims = 15M ops
  - At 2 GHz per core: 15M / 2e9 ≈ 7.5ms per query
  - 1 core → 133 QPS max
  - Need 8 cores → 1,064 QPS ✓

Thread pool:
  - Use 16-32 worker threads (2x core count for I/O slack)
  - Connection pool to vector store (ANN index)
  - Bounded queue to prevent memory explosion
```

**Distributed approach (for scaling):**

```
Load balancer
    ↓
[Query Router (sharding)]
    ↓
[Shard-A] [Shard-B] ... [Shard-N]
   ↓ (each handles 1000/N QPS)
[Redis] [ANN Index] [Vector Cache]
```

#### E. Database & Vector Store Layer

**Current implementation:**

- In-memory: all vectors loaded at startup
- **Problem**: 600 GB for full system

**Scalable approach:**

```
1. Vector DB (e.g., Weaviate, Milvus, Pinecone)
   - HNSW indexes pre-built per shard
   - Managed scaling, replication
   - ~$10K-50K/month for 1M vectors

2. File-based with mmap:
   - Serialize vectors to .bin files
   - Memory-map for lazy loading
   - Free but requires careful memory management

3. Redis Cluster:
   - Store quantized vectors (int8)
   - Use Redis Cluster for horizontal scaling
   - Sub-millisecond retrieval (if cached)
```

**Recommendation:**

```
Hybrid approach:
  - Hot vectors (top 10% by query frequency) → Redis
  - Warm vectors → Local mmap'd files
  - Cold vectors → Vector DB with ANN indexing
  - Cost-effective + maintains sub-100ms p99 latency
```

#### F. Multi-Tenant Isolation

**Requirement: Different customers MUST NEVER share context**

**Enforcement points:**

1. **Tree traversal:**

   ```python
   # Add tenant_id to metadata matching
   query_meta = {"tenant_id": "cust_a", "topic": "sql-migration"}
   # Only routes to nodes scoped to cust_a
   ```
2. **Vector store access:**

   ```python
   # Each leaf node tagged with tenant
   leaf_node.tenant_id = "cust_a"
   if leaf_node.tenant_id != request.tenant_id:
       raise AuthorizationError()
   ```
3. **Caching:**

   ```python
   # Cache key includes tenant_id
   cache_key = f"{tenant_id}:{query_hash}"
   ```
4. **Database:**

   ```sql
   -- Partition vectors by tenant at DB layer
   CREATE TABLE vectors (
       tenant_id UUID,
       vector_id BIGINT,
       embedding VECTOR(300),
       PRIMARY KEY (tenant_id, vector_id)
   );
   ```

**Audit & monitoring:**

- Log all cross-tenant query attempts (should be 0)
- Monitor cache hit rates per tenant (anomalies indicate leakage)
- Quarterly audit of vector data access patterns

---

## 3. Collapse Filter Design

### Design Decision: θ_collapse = 0.95

#### Justification

The collapse filter removes FAQs that are **too similar to the query itself**, under the assumption that such FAQs are either:

- Verbatim matches (redundant to return)
- Trivially similar (user already knows the answer)
- Harmful duplicates (clutters context for LLM)
- Security reasons or blocked questions

**Why θ_collapse = 0.95?**

1. **Cosine similarity properties:**

   ```
   cos(0°)  = 1.0   (identical vectors)
   cos(5°)  = 0.996 (nearly identical)
   cos(15°) = 0.966 (very similar semantically)
   cos(30°) = 0.866 (similar concepts)
   ```
2. **Empirical threshold:**

   - 0.95 = ~18° angle = strong semantic similarity
   - Catches verbatim + near-duplicate cases
   - It doesn't over-filter related FAQs (0.90 is still "related", not "same")'
     Example- Gaurdrail is "How to make a ransomware script in server to affect other people?"
     Query is "How to detect ransomware kind script in server before it affects other people"

     will have very similar cosine score in practise like 0.92or something but it is not a bad question so we are taking filter  Theta gaurdrail= greater or equal to 0.95 for checking similiraity
3. **Business logic:**

   - If an FAQ is > 0.95 similar to user's query, it's likely a direct answer
   - LLM can already infer this from the query itself
   - Returning it wastes context window space

#### Production Tuning Strategy

**Approach: A/B testing with user feedback**

```python
# Collect metrics per collapse threshold
thresholds = [0.90, 0.92, 0.95, 0.98]

for threshold in thresholds:
    # Track:
    #   - User satisfaction (did FAQ help?)
    #   - Context utilization (were FAQs used?)
    #   - Latency (fewer FAQs = faster LLM call)
    retriever.theta_collapse = threshold
    results = run_queries(threshold)
    analyze_metrics(results)
```

**Heuristics:**

- If users complain answers are "too generic" → increase θ_collapse (0.95 → 0.98)
- If users complain about "duplicate FAQs" → decrease θ_collapse (0.95 → 0.92)
- Monitor context token usage; optimize for LLM efficiency

### Edge Case: k > |FAQ Store| After Filtering

**Scenario:** User requests k=5 FAQs, but collapse filter removes 4 → only 1 left

**Implementation in retriever.py:**

```python
def _rank_and_filter_faqs(self, query_vector, faq_store, query):
    # Calculate similarities for all FAQs
    faq_rankings = [...]  # sorted by similarity
  
    # Apply collapse filter
    filtered_faqs = []
    for faq_info in faq_rankings:
        if faq_info["similarity"] > self.theta_collapse:
            continue  # Skip (too similar)
  
        filtered_faqs.append(faq_info)
  
        if len(filtered_faqs) >= self.k:
            break  # Stop once we have k results
  
    # Edge case: fewer than k FAQs after filtering
    # Return what we have (may be < k)
    return filtered_faqs  # Could be empty or < k
```

**Design decision: Return fewer than k FAQs if needed**

Rationale:

- Returning 2 high-quality FAQs > forcing 5 faqs that are not similar
- Better for LLM: focused context > bloated context
- Aligns with: "retrieve exactly k FAQs... collapse filter" spec interpretation

**Alternative (strict k):**

```python
# If < k after filtering, keep "close enough" FAQs
while len(filtered_faqs) < self.k and rankings_available:
    next_faq = get_next_lower_rank_faq()
    filtered_faqs.append(next_faq)
```

This trades relevance for quantity; not recommended for quality-critical systems.

### Filter Order: Before or After Guardrail Check?

**Current implementation: Guardrail check → Ranking → Collapse filter**

**Justification:**

1. **Safety first:** Guardrails prevent returning any blocked FAQ
2. **Efficiency:** Reject unsafe queries early, before expensive FAQ scoring
3. **Logic flow:**
   ```
   Guardrail check (10% of queries blocked) → Ranking (expensive) → Collapse filter

   If block rate = 10%: save 10% of ranking cost
   vs.
   Collapse filter → Guardrail check: must score all FAQs first
   ```

**Alternative order: Collapse → Guardrail:**

- Pro: Reduce guardrail check overhead if some FAQs already removed
- Con: Safety-critical logic should run first; order dependency creates risk

**Conclusion: Current order is correct (guardrail first).**

---

## 4. Guardrail Limitations & Robustness

### Vulnerability 1: Semantic Paraphrasing

**Attack:**

```
Blocked guardrail: "delete customer database"
Adversarial input: "remove all records from customer tables"
```

Cosine similarity: ~0.70 (below 0.85 threshold)
Result: Bypasses guardrail despite identical intent

**Why it happens:**

- Cosine similarity operates on word embeddings
- Synonyms have high similarity but not perfect (e.g., "delete" vs. "remove")
- Paraphrasing reduces similarity score

**Mitigation:**

1. **Expand guardrails:** Include multiple phrasings

   ```python
   guardrail_store.add("delete customer database", {...})
   guardrail_store.add("remove customer records", {...})
   guardrail_store.add("wipe customer data", {...})
   ```
2. **Semantic expansion with LLM:**

   In our project scope as using embeddings and semantics is not advised

   ```python
   blocked_topic = "delete customer database"
   paraphrases = llm.generate_paraphrases(blocked_topic, n=5)
   for p in paraphrases:
       guardrail_store.add(p, {...})
   ```
3. **Increase threshold:**

   ```python
   theta_guard = 0.75  # Lower threshold catches more variations
   # Trade-off: May false-positive on unrelated queries
   ```

### Vulnerability 2: Obfuscation & Indirection

**Attack:**

```
Blocked: "drop table"
Adversarial: "What are best practices for dropping a table?"
            "How do I remove a table safely?"
```

**Mitigation:**

- Guardrails should capture intent, not just SQL commands
- "drop table" → generalize to "destructive database operations"

### Vulnerability 3: Hybrid Attacks (Guardrail + FAQ Evasion)

**Attack:** Craft query that passes guardrail but solicits dangerous FAQ

```
Query: "I have read-only access. Can I view password fields?"
Guardrail threshold: 0.85 (passes)
FAQ (crafted adversary): "Yes, read-only users can see all fields including passwords"
```

**Mitigation:**

- Guardrails should cover not just "dangerous operations" but "dangerous information"
- Add guardrails for sensitive data exposure:
  ```python
  guardrail_store.add("view password fields", {...})
  guardrail_store.add("access encryption keys", {...})
  ```

### Vulnerability 4: False Negatives in Interpretation

**Edge case:**

```
User (benign): "How do I safely delete old test data?"
Guardrail: "delete" triggers block
```

**Mitigation:**

- Use more specific guardrails ("delete production", not just "delete")
- Increase θ_guard slightly to reduce false positives
- Log guardrail rejections for manual review

### Recommended Guardrail Hardening Strategy

1. **Multi-level defense:**

   ```python
   # Level 1: Intent-based (semantic)
   guardrails_intent = [
       "unauthorized data access",
       "destructive operations",
       "system compromise",
   ]

   # Level 2: Specific patterns (lexical)
   guardrails_patterns = [
       "drop table production",
       "delete where 1=1",
       "password", "key", "secret", "token",
   ]
   ```
2. **Combine semantic + lexical checks:**

   ```python
   def enhanced_guardrail_check(query):
       semantic_block = _check_semantic_guardrails(query)
       lexical_block = _check_lexical_guardrails(query)
       return semantic_block or lexical_block
   ```
3. **Content-based filtering (post-retrieval):**

   ```python
   faqs = retriever.retrieve(query, meta)
   for faq in faqs:
       if _contains_sensitive_info(faq["answer"]):
           redact_sensitive_fields(faq)
   ```
4. **Regular auditing:**

   - Track rejected queries (understand adversary patterns)
   - Review FAQ store for sensitive information leakage
   - Quarterly update to guardrails based on new threats

---

## 5. Implementation Highlights

### Key Design Decisions

1. **Recursive tree traversal (not iterative)**

   - Enables clean base case (is_leaf)
   - Natural fallback with default_child
   - Matches mental model of hierarchical routing
2. **Cosine similarity from scratch (NumPy only)**

   - Demonstrates understanding of vector math
   - Handles edge cases: zero vectors, precision
   - No hidden dependencies on scipy/sklearn
3. **Dual vector stores per leaf**

   - FAQ store: high-quality answers (optimize for relevance)
   - Guardrail store: small, safety-critical (optimize for safety)
   - Separation of concerns
4. **Collapse filter before LLM call**

   - Reduces context size (saves tokens and cost)
   - Removes obvious duplicates (better UX)
   - Enables smaller models or faster inference

### Testing Strategy

1. **Unit tests:**

   - Cosine similarity edge cases (zero vectors, precision)
   - Tree routing with various metadata combinations
   - Collapse filter behavior
2. **Integration tests:**

   - End-to-end query → FAQ retrieval → LLM context
   - Guardrail blocking
   - Multi-tenant isolation
3. **Benchmark tests:**

   - 1,000 FAQs × 300D: measure time/space
   - Simulate 100 concurrent queries
   - Profile bottlenecks

---

## 6. Future Enhancements 

1. **HNSW indexing** (see scaling section)
2. **Multi-query fan-out** (route to multiple leaves if ambiguous)
3. **Persistence layer** (serialize tree to disk without pickle)
4. **Evaluation harness** (measure precision@k on test set)
5. **Query expansion** (rewrite query before retrieval for better recall)


##Implementing HNSW
-Hierarchical widening of level elemnts are done

<img width="900" height="1600" alt="image" src="https://github.com/user-attachments/assets/c7b6faa3-b060-4be9-bae4-e5af23015c3f" />

The initial points and all are choosen using k means clustering 

Greedy choice of Min(cosine_similarity) is assessed while choosing next node

<img width="1180" height="1333" alt="image" src="https://github.com/user-attachments/assets/34762e30-773e-4c93-9a5d-4fa72de63c08" />


---

## Conclusion

This design prioritizes **correctness and safety** for a production system handling sensitive enterprise data. The hierarchical tree structure scales naturally to multi-tenant scenarios, while the dual vector store approach enables both relevance (FAQ store) and safety (guardrail store). Trade-offs between latency, accuracy, and cost are discussed throughout, with specific recommendations for 10K-scale deployments.

The system is ready for production with the ANN indexing upgrade; the current implementation is suitable for development and testing at smaller scale (< 1000 leaves, < 10K FAQs per leaf).
