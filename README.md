# Tree-Structured Vector Retrieval System - Novuz CMaaP

A production-ready hierarchical vector retrieval system for enterprise data warehouse migration queries. Built with pure Python, NumPy, and FastText embeddings.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Query Input (user question)                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│            1. TREE TRAVERSAL (Recursive Routing)                 │
│  Match query metadata → Navigate hierarchical tree → Leaf node   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│         2. GUARDRAIL CHECK (Safety & Security)                   │
│   Check if query violates blocked topics → Raise exception if hit│
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│   3. FAQ RANKING & 4. COLLAPSE FILTER (Relevance & Dedup)        │
│  Score FAQs by cosine similarity → Remove near-duplicates       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│         5. LLM CONTEXT FORMATTING & API CALL                     │
│        Format top-k FAQs → Call Claude/OpenAI LLM               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
                 [LLM Response]
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- Virtual environment (already created in `vir/`)

### Installation

1. **Activate the virtual environment:**
   ```bash
   # On Windows (PowerShell)
   .\vir\Scripts\Activate.ps1
   
   # On Windows (Command Prompt)
   vir\Scripts\activate.bat
   
   # On macOS/Linux
   source vir/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   This installs:
   - `fasttext==0.9.3` - FastText embeddings (300-dimensional)
   - `numpy==2.4.5` - Array operations (dot product, norm)
   - `requests==2.31.0` - Optional: HTTP calls to LLM APIs
   - `httpx==0.25.2` - Optional: Async HTTP client

3. **Verify FastText model download:**
   ```bash
   python -c "import fasttext; import fasttext.util; fasttext.util.download_model('en', if_exists='ignore')"
   ```
   This downloads the 300-dimensional multilingual FastText model (~1.2 GB, cached in `~/.fasttext`).

### Configuration

**LLM Provider (Optional):**
To enable actual LLM API calls (not required for demo), set environment variables:

```bash
# For Claude (Anthropic)
$env:ANTHROPIC_API_KEY = "your_anthropic_api_key"

# For OpenAI
$env:OPENAI_API_KEY = "your_openai_api_key"
```

Without these, the system runs in **demo mode** and prints formatted responses showing how the LLM would be called.

## Running the Demo

### Execute Main Demo
```bash
python main.py
```

### Expected Output
The demo will:
1. Build a 5-leaf hierarchical routing tree
2. Populate each leaf with FAQs and guardrails
3. Run 3 sample queries through the full pipeline
4. Display retrieved FAQs with similarity scores
5. Show LLM context formatting

**Sample output snippet:**
```
================================================================================
NOVUZ CMAAP - TREE-STRUCTURED VECTOR RETRIEVAL SYSTEM DEMO
================================================================================

🚀 Initializing Novuz CMaaP Vector Retrieval System...

📦 Building hierarchical routing tree...
✅ Tree structure created with 5 leaf nodes
   - T-SQL Migration
   - Teradata Migration
   - General SQL Migration (default)
   - SSIS Migration
   - General CMaaP (default)

🔍 Initializing retriever...
✅ Retriever initialized
   - k = 5 FAQs to retrieve
   - Guardrail threshold = 0.85
   - Collapse filter threshold = 0.95
   - Pick threshold = 0.3

💬 Initializing LLM client...
✅ LLM client ready (Provider: CLAUDE, Model: claude-3-haiku-20250122)

📝 Running sample queries...

================================================================================
QUERY 1: T-SQL specific query - routes to T-SQL leaf
================================================================================

Query: How do I convert SQL Server CAST functions to be compatible with Teradata?
Routing Metadata: {'product': 'cmaap', 'topic': 'sql-migration', 'dialect': 'tsql'}

✅ Successfully retrieved 3 FAQs

  FAQ 1 (similarity: 0.847)
    Q: How do I convert SQL Server CAST to standard SQL?
    A: Use CAST() function which is standard SQL-92. Example: CAST(column AS VARCHAR(10))

  FAQ 2 (similarity: 0.523)
    Q: What's the difference between GETDATE() and SYSDATETIME()?
    A: GETDATE() returns DATETIME, SYSDATETIME() returns DATETIME2. Use SYSDATETIME() for better precision.

  FAQ 3 (similarity: 0.412)
    Q: How do I handle T-SQL specific data types?
    A: T-SQL specific types: UNIQUEIDENTIFIER -> UUID, NVARCHAR -> VARCHAR with UTF-8 collation, TEXT -> CLOB
```

## Project Structure

```
c:\Users\Anu18bhab\Desktop\Codes\Novaruz\
├── tree.py                 # Tree traversal & routing logic
│   ├── TreeNode            # Internal tree nodes with metadata
│   ├── LeafNode            # Leaf nodes with FAQ + guardrail stores
│   └── RoutingTree         # Main tree container with recursive traverse()
│
├── vector_store.py         # Vector storage & similarity search
│   ├── VectorStore         # Vectorization, similarity, persistence
│   └── cosine_similarity() # Pure Python cosine implementation
│
├── retriever.py            # Full retrieval pipeline
│   ├── Retriever           # Orchestrates all pipeline stages
│   ├── GuardrailException  # Safety rejection exception
│   └── [Methods]
│       ├── _check_guardrails()      # Step 2
│       ├── _rank_and_filter_faqs()  # Steps 3-4
│       └── format_context()         # Step 5
│
├── llm_client.py           # Claude/OpenAI wrapper
│   ├── LLMClient           # Provider abstraction
│   └── create_llm_client() # Factory function
│
├── main.py                 # Demo: build tree, run 3 queries
│   ├── build_sample_tree() # Create 5-leaf hierarchical tree
│   └── run_sample_queries()# Execute queries with results
│
├── DESIGN.md               # Complexity analysis & scaling
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Key Features

### 1. Hierarchical Routing Tree
- **Arbitrary branching factor** (not limited to binary)
- **Recursive traversal** with clean base case
- **Metadata-aware matching** (e.g., product, topic, dialect)
- **Graceful fallback** via default_child if no match

### 2. Dual Vector Stores per Leaf
- **FAQ Store**: High-relevance question-answer pairs (vectorized)
- **Guardrail Store**: Blocked topics for safety (small, high-priority)

### 3. Complete Retrieval Algorithm
```
Step 1: Vectorize query         → FastText 300-dim embedding
Step 2: Guardrail check         → Reject if too similar to blocked topics
Step 3: Initial ranking         → Score all FAQs by cosine similarity
Step 4: Collapse filter         → Remove FAQs too similar to query
Step 5: LLM context formatting  → Combine k FAQs for LLM
```

### 4. Cosine Similarity from Scratch
- Pure NumPy implementation (no sklearn/scipy)
- Handles edge cases: zero vectors, dimension mismatches, floating-point precision
- O(D) where D = vector dimension

### 5. Multi-Tenant Safety
- Query metadata includes tenant routing
- Guardrails enforce access control
- LLMClient supports API key management

## Complexity Analysis

See [DESIGN.md](./DESIGN.md) for complete analysis.

### Time Complexity: O(D·(G + F))
- D = vector dimension (300)
- G = guardrails per leaf (~20)
- F = FAQs per leaf (1,000)
- **Total**: ~315K operations per query (~5-10ms)

### Space Complexity: O(D·(N + F_total))
- N = tree nodes
- F_total = total FAQs across all leaves
- **For 10K leaves × 50K FAQs**: ~600 GB (uncompressed)

### Bottleneck
- **Primary**: FAQ ranking (O(F·D)) — linear scan of all vectors
- **Solution at scale**: HNSW indexing (O(log F·D))

## Scaling to Production (10,000 Leaves × 50K FAQs × 1,000 QPS)

See [DESIGN.md](./DESIGN.md) Section 2 for detailed strategies:

1. **Tenant-based sharding** — Multi-tenant isolation
2. **HNSW indexing** — Replace linear scan (~3000x speedup)
3. **Multi-level caching** — Query cache, vector cache, guardrail cache
4. **Distributed deployment** — Load balancing, thread pools
5. **Vector DB integration** — Managed scaling (Weaviate, Milvus, Pinecone)

## Guardrail Limitations & Hardening

See [DESIGN.md](./DESIGN.md) Section 4 for security analysis:

- **Semantic paraphrasing attacks** → Expand guardrails, increase threshold
- **Obfuscation & indirection** → Capture intent, not just keywords
- **Sensitive data leakage** → Add post-retrieval content filtering
- **Recommended**: Multi-level defense (intent-based + lexical patterns)

## Testing

### Run Unit Tests (Example)
```python
# Test cosine similarity edge cases
from vector_store import VectorStore

# Zero vectors
assert VectorStore.cosine_similarity([0, 0, 0], [0, 0, 0]) == 0.0

# Identical vectors
assert VectorStore.cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0

# Perpendicular vectors
assert abs(VectorStore.cosine_similarity([1, 0, 0], [0, 1, 0]) - 0.0) < 1e-6

# Dimension mismatch
try:
    VectorStore.cosine_similarity([1, 2], [1, 2, 3])
    assert False, "Should raise ValueError"
except ValueError:
    pass

print("✅ All cosine similarity tests passed!")
```

### Integration Test
```bash
python main.py
# Check for:
# ✅ Tree routing works
# ✅ Guardrails block correctly
# ✅ Collapse filter produces ≤ k results
# ✅ LLM context formats properly
```

## LLM Provider Configuration

### Claude (Anthropic) - Default
```python
from llm_client import create_llm_client

client = create_llm_client("claude")
# Uses model: claude-3-haiku-20250122 (latest)
# Requires: $env:ANTHROPIC_API_KEY
```

### OpenAI
```python
from llm_client import create_llm_client

client = create_llm_client("openai")
# Uses model: gpt-4
# Requires: $env:OPENAI_API_KEY
```

### Demo Mode (No API Key)
```python
# If API key not set, prints formatted response showing LLM would be called
response = client.query(context, question)
# Output includes: question, context, and placeholder for LLM response
```

## Implementation Highlights

### Why Recursive Tree Traversal?
- Matches hierarchical routing mental model
- Clean base case: `if self.is_leaf(): return self`
- Natural fallback: `if no match: return self.default_child.route(query_meta)`
- No globals, pure functional approach

### Why Cosine Similarity from Scratch?
- Demonstrates vector math understanding
- No hidden dependencies on scipy/sklearn
- Explicit handling of edge cases (zero vectors, precision)
- Correctness auditable

### Why Collapse Filter at 0.95 Similarity?
- Catches verbatim matches + near-duplicates
- ~18° angle = strong semantic similarity (essentially the same concept)
- Reduces context clutter for LLM
- Tunable in production via A/B testing

## Common Issues & Troubleshooting

### FastText Model Download Fails
```
Error: Cannot download 'cc.en.300.bin'
Solution: 
  1. Check internet connection
  2. Manually download: https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz
  3. Extract and place in ~/.fasttext/
```

### Out of Memory
```
Error: Cannot load vector stores (600 GB for 10K leaves)
Solution:
  1. Reduce FAQ store size (test with 100 FAQs per leaf)
  2. Use ANN indexing + mmap (see DESIGN.md)
  3. Implement vector DB layer (Weaviate, Pinecone)
```

### Queries Not Matching Expected Leaf
```
Issue: Query routes to wrong leaf despite metadata
Debug:
  retriever.tree.traverse(query_meta)  # Check actual routing
  print(routing_path)                  # Trace metadata matching
```

### Guardrail False Positives
```
Issue: Legitimate query blocked by guardrail
Solution:
  1. Increase theta_guard (0.85 → 0.88)
  2. Review guardrail wording (too generic?)
  3. Add benign variations to FAQ store
```

## References

- **FastText**: https://fasttext.cc/ (Word embeddings, 300-dim)
- **Cosine Similarity**: https://en.wikipedia.org/wiki/Cosine_similarity
- **HNSW Indexing**: https://arxiv.org/abs/1802.02413 (Scaling strategy)
- **Novuz CMaaP**: Enterprise data warehouse migration platform

## Submission

This project is submitted to Novuz Inc. as part of the Senior Python Engineer take-home interview.

- **GitHub Repo**: `rag-tree-<your-github-handle>`
- **Design Doc**: [DESIGN.md](./DESIGN.md)
- **Contact**: subhajit@novuz.com (questions/support)

---

**Built with:** Python 3.11+ | NumPy | FastText | Pure Python implementations
**Status:** Production-ready for single-machine deployments; see DESIGN.md for scaling strategies
**Last Updated:** 2026-05-16
