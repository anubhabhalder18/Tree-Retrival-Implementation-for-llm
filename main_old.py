

import os
from tree import TreeNode, LeafNode, RoutingTree
from vector_store import VectorStore
from retriever import Retriever, GuardrailException
from llm_client import create_llm_client


def build_sample_tree() -> RoutingTree:
    
    #tsql
    tsql_faq = VectorStore("tsql_faq")
    tsql_faq.add(
        "How do I convert SQL Server CAST to standard SQL?",
        {
            "question": "How do I convert SQL Server CAST to standard SQL?",
            "answer": "Use CAST() function which is standard SQL-92. Example: CAST(column AS VARCHAR(10))",
        },
    )
    tsql_faq.add(
        "What's the difference between GETDATE() and SYSDATETIME()?",
        {
            "question": "What's the difference between GETDATE() and SYSDATETIME()?",
            "answer": "GETDATE() returns DATETIME, SYSDATETIME() returns DATETIME2. Use SYSDATETIME() for better precision.",
        },
    )
    tsql_faq.add(
        "How do I handle T-SQL specific data types?",
        {
            "question": "How do I handle T-SQL specific data types?",
            "answer": "T-SQL specific types: UNIQUEIDENTIFIER -> UUID, NVARCHAR -> VARCHAR with UTF-8 collation, TEXT -> CLOB",
        },
    )

    tsql_guardrail = VectorStore("tsql_guardrail")
    tsql_guardrail.add("hacking attacks SQL injection", {"blocked_reason": "Security threat"})
    tsql_guardrail.add("drop table production", {"blocked_reason": "Dangerous operation"})

    tsql_leaf = LeafNode(faq_store=tsql_faq, guardrail_store=tsql_guardrail)
    tsql_node = TreeNode(
        metadata={"product": "cmaap", "topic": "sql-migration", "dialect": "tsql"},
        leaf=tsql_leaf,
    )


    teradata_faq = VectorStore("teradata_faq")
    teradata_faq.add(
        "How do I convert Teradata CAST functions?",
        {
            "question": "How do I convert Teradata CAST functions?",
            "answer": "Teradata CAST is similar to standard SQL. Main difference: CAST(col AS CHAR(10)) vs CAST(col AS VARCHAR(10))",
        },
    )
    teradata_faq.add(
        "What about Teradata temporal tables?",
        {
            "question": "What about Teradata temporal tables?",
            "answer": "Teradata uses VERSIONING clause. Convert to standard SQL temporal tables or maintain version history in separate tables.",
        },
    )
    teradata_faq.add(
        "How do I handle Teradata specific functions?",
        {
            "question": "How do I handle Teradata specific functions?",
            "answer": "CURRENT_TIMESTAMP works in both. For Teradata specifics: EXTRACT, SUBSTR, CAST all have standard SQL equivalents.",
        },
    )

    teradata_guardrail = VectorStore("teradata_guardrail")
    teradata_guardrail.add("terminate database", {"blocked_reason": "Dangerous operation"})
    teradata_guardrail.add("malicious code execution", {"blocked_reason": "Security threat"})

    teradata_leaf = LeafNode(faq_store=teradata_faq, guardrail_store=teradata_guardrail)
    teradata_node = TreeNode(
        metadata={"product": "cmaap", "topic": "sql-migration", "dialect": "teradata"},
        leaf=teradata_leaf,
    )

    # ============================================================================
    # LEAF 3: General SQL Migration (default)
    # ============================================================================
    general_sql_faq = VectorStore("general_sql_faq")
    general_sql_faq.add(
        "What's the migration process for SQL dialects?",
        {
            "question": "What's the migration process for SQL dialects?",
            "answer": "1. Analyze source schema and queries, 2. Map data types, 3. Convert dialect-specific functions, 4. Test thoroughly",
        },
    )
    general_sql_faq.add(
        "How do I handle stored procedures across dialects?",
        {
            "question": "How do I handle stored procedures across dialects?",
            "answer": "Extract business logic, convert syntax, test with sample data. Consider refactoring complex procedures.",
        },
    )
    general_sql_faq.add(
        "What are common migration pitfalls?",
        {
            "question": "What are common migration pitfalls?",
            "answer": "Implicit type conversions, date/time handling, NULL semantics, and performance regression. Plan thorough testing.",
        },
    )

    general_guardrail = VectorStore("general_guardrail")
    general_guardrail.add("unauthorized access database", {"blocked_reason": "Security threat"})

    general_leaf = LeafNode(faq_store=general_sql_faq, guardrail_store=general_guardrail)
    general_sql_node = TreeNode(
        metadata={"product": "cmaap", "topic": "sql-migration"},
        leaf=general_leaf,
    )

    # ============================================================================
    # LEAF 4: SSIS Migration
    # ============================================================================
    ssis_faq = VectorStore("ssis_faq")
    ssis_faq.add(
        "How do I migrate SSIS packages?",
        {
            "question": "How do I migrate SSIS packages?",
            "answer": "Convert SSIS to Apache Airflow, Talend, or cloud ETL tools. Extract control flow and data flow logic.",
        },
    )
    ssis_faq.add(
        "What about SSIS transformations?",
        {
            "question": "What about SSIS transformations?",
            "answer": "SSIS transformations map to Python/SQL equivalents. Use pandas for data transformation or SQL transformations.",
        },
    )
    ssis_faq.add(
        "How do I test SSIS migrations?",
        {
            "question": "How do I test SSIS migrations?",
            "answer": "Validate data quality, compare row counts, test error handling, verify performance on representative data volumes.",
        },
    )

    ssis_guardrail = VectorStore("ssis_guardrail")
    ssis_guardrail.add("delete production data", {"blocked_reason": "Dangerous operation"})

    ssis_leaf = LeafNode(faq_store=ssis_faq, guardrail_store=ssis_guardrail)
    ssis_node = TreeNode(
        metadata={"product": "cmaap", "topic": "ssis-migration"},
        leaf=ssis_leaf,
    )

    # ============================================================================
    # LEAF 5: General CMaaP (default)
    # ============================================================================
    cmaap_general_faq = VectorStore("cmaap_general_faq")
    cmaap_general_faq.add(
        "What is CMaaP?",
        {
            "question": "What is CMaaP?",
            "answer": "CMaaP (Continuous Modernization as a Product) is Novuz's SaaS platform for enterprise data warehouse migration.",
        },
    )
    cmaap_general_faq.add(
        "What databases does CMaaP support?",
        {
            "question": "What databases does CMaaP support?",
            "answer": "CMaaP supports SQL Server (T-SQL), Teradata, Snowflake, BigQuery, Redshift, and other modern data warehouses.",
        },
    )
    cmaap_general_faq.add(
        "How do I get started with CMaaP?",
        {
            "question": "How do I get started with CMaaP?",
            "answer": "1. Create account, 2. Connect source database, 3. Analyze schema, 4. Configure migration rules, 5. Test and deploy.",
        },
    )

    cmaap_guardrail = VectorStore("cmaap_guardrail")
    cmaap_guardrail.add("delete customer database", {"blocked_reason": "Dangerous operation"})
    cmaap_guardrail.add("steal data confidential", {"blocked_reason": "Security threat"})

    cmaap_leaf = LeafNode(faq_store=cmaap_general_faq, guardrail_store=cmaap_guardrail)
    cmaap_node = TreeNode(
        metadata={"product": "cmaap"},
        leaf=cmaap_leaf,
    )

    # ============================================================================
    # Build tree structure
    # ============================================================================
    sql_migration_node = TreeNode(
        metadata={"product": "cmaap", "topic": "sql-migration"},
        children=[tsql_node, teradata_node],
        default_child=general_sql_node,
    )

    root = TreeNode(
        metadata={"product": "cmaap"},
        children=[sql_migration_node, ssis_node],
        default_child=cmaap_node,
    )

    return RoutingTree(root)


def run_sample_queries(retriever: Retriever, llm_client):
    """
    Run 3 sample queries through the retrieval pipeline.

    Args:
        retriever: Retriever instance with tree and configuration
        llm_client: LLMClient for formatting responses
    """
    queries = [
        {
            "query": "How do I convert SQL Server CAST functions to be compatible with Teradata?",
            "meta": {"product": "cmaap", "topic": "sql-migration", "dialect": "tsql"},
            "description": "T-SQL specific query - routes to T-SQL leaf",
        },
        {
            "query": "What's the migration process for stored procedures?",
            "meta": {"product": "cmaap", "topic": "sql-migration"},
            "description": "General SQL migration - routes to default SQL leaf",
        },
        {
            "query": "How do I migrate SSIS packages to cloud ETL?",
            "meta": {"product": "cmaap", "topic": "ssis-migration"},
            "description": "SSIS query - routes to SSIS leaf",
        },
    ]

    print("=" * 80)
    print("NOVUZ CMAAP - TREE-STRUCTURED VECTOR RETRIEVAL SYSTEM DEMO")
    print("=" * 80)
    print()

    for i, query_info in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"QUERY {i}: {query_info['description']}")
        print(f"{'=' * 80}")
        print(f"\nQuery: {query_info['query']}")
        print(f"Routing Metadata: {query_info['meta']}")

        try:
            # Run the full retrieval pipeline
            faqs = retriever.retrieve(query_info["query"], query_info["meta"])

            print(f"\n✅ Successfully retrieved {len(faqs)} FAQs\n")

            # Display retrieved FAQs
            for j, faq in enumerate(faqs, 1):
                similarity = faq.get("_similarity_score", 0.0)
                print(f"  FAQ {j} (similarity: {similarity:.3f})")
                print(f"    Q: {faq.get('question', 'N/A')}")
                print(f"    A: {faq.get('answer', 'N/A')}\n")

            # Format context and show LLM response
            context = Retriever.format_context(faqs)
            print("LLM Context:")
            print(context)
            print()

            # Show LLM response (demo mode)
            print("\n" + "-" * 80)
            print("LLM Response:")
            print("-" * 80)
            response = llm_client.query(context, query_info["query"])
            print(response)

        except GuardrailException as e:
            print(f"\n Guardrail Violation: {e}")


def main():
    """Main entry point: Build tree, initialize retriever, run sample queries."""

    print("\n🚀 Initializing Novuz CMaaP Vector Retrieval System...\n")

    data_dir = "./data"
    tree_path = os.path.join(data_dir, "tree_structure.json")

    # Check for existing persisted data
    if os.path.exists(tree_path):
        print(f"Loading existing routing tree from {data_dir}...")
        tree = RoutingTree.load(data_dir)
        print("Tree loaded from disk")
    else:
        print("Building hierarchical routing tree from scratch...")
        tree = build_sample_tree()
        print("Persisting tree structure and vector stores...")
        tree.save(data_dir)
        print("Tree structure created and saved to disk")
        print("   - T-SQL Migration")
        print("   - Teradata Migration")
        print("   - General SQL Migration (default)")
        print("   - SSIS Migration")
        print("   - General CMaaP (default)")

    # Initialize retriever
    print("\n🔍 Initializing retriever...")
    retriever = Retriever(
        tree=tree,
        k=5,  # Retrieve top 5 FAQs
        theta_guard=0.85,  # Guardrail threshold
        theta_collapse=0.95,  # Collapse filter threshold
        pick_threshold=0.3,  # Minimum similarity to include FAQ
    )
    print("Retriever initialized")
    print(f"   - k = {retriever.k} FAQs to retrieve")
    print(f"   - Guardrail threshold = {retriever.theta_guard}")
    print(f"   - Collapse filter threshold = {retriever.theta_collapse}")
    print(f"   - Pick threshold = {retriever.pick_threshold}")

    # Initialize LLM client
    print("\n itializing LLM client...")
    llm_client = create_llm_client("claude")
    print(f"LLM client ready (Provider: {llm_client.provider.value.upper()}, Model: {llm_client.model})")

    # Run sample queries
    print("\n📝 Running sample queries...\n")
    run_sample_queries(retriever, llm_client)

    print("\n" + "=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
