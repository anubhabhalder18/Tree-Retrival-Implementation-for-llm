"""
FastAPI server version of the demo script.

Run:
    uvicorn server_new:app --reload
"""

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tree import RoutingTree
from retriever import Retriever, GuardrailException




from tree import TreeNode, LeafNode, RoutingTree
from vector_store import VectorStore


def build_sample_tree() -> RoutingTree:

    # =========================================================
    # T-SQL LEAF
    # =========================================================

    tsql_faq = VectorStore("tsql_faq")

    tsql_faq.add(
        "How do I convert SQL Server CAST to standard SQL?",
        {
            "question": "How do I convert SQL Server CAST to standard SQL?",
            "answer": "Use CAST() function which is standard SQL-92."
        }
    )

    tsql_faq.add(
        "What's the difference between GETDATE() and SYSDATETIME()?",
        {
            "question": "What's the difference between GETDATE() and SYSDATETIME()?",
            "answer": "GETDATE() returns DATETIME while SYSDATETIME() returns DATETIME2."
        }
    )

    tsql_guardrail = VectorStore("tsql_guardrail")

    tsql_guardrail.add(
        "hacking attacks SQL injection",
        {
            "blocked_reason": "Security threat"
        }
    )

    tsql_leaf = LeafNode(
        faq_store=tsql_faq,
        guardrail_store=tsql_guardrail
    )

    tsql_node = TreeNode(
        metadata={
            "product": "cmaap",
            "topic": "sql-migration",
            "dialect": "tsql"
        },
        leaf=tsql_leaf
    )

    # =========================================================
    # TERADATA LEAF
    # =========================================================

    teradata_faq = VectorStore("teradata_faq")

    teradata_faq.add(
        "How do I convert Teradata CAST functions?",
        {
            "question": "How do I convert Teradata CAST functions?",
            "answer": "Teradata CAST is similar to standard SQL."
        }
    )

    teradata_guardrail = VectorStore("teradata_guardrail")

    teradata_guardrail.add(
        "terminate database",
        {
            "blocked_reason": "Dangerous operation"
        }
    )

    teradata_leaf = LeafNode(
        faq_store=teradata_faq,
        guardrail_store=teradata_guardrail
    )

    teradata_node = TreeNode(
        metadata={
            "product": "cmaap",
            "topic": "sql-migration",
            "dialect": "teradata"
        },
        leaf=teradata_leaf
    )

    # =========================================================
    # GENERAL SQL LEAF
    # =========================================================

    general_sql_faq = VectorStore("general_sql_faq")

    general_sql_faq.add(
        "What's the migration process for SQL dialects?",
        {
            "question": "What's the migration process for SQL dialects?",
            "answer": "Analyze schema, map types, convert functions, and test thoroughly."
        }
    )

    general_guardrail = VectorStore("general_guardrail")

    general_guardrail.add(
        "unauthorized access database",
        {
            "blocked_reason": "Security threat"
        }
    )

    general_leaf = LeafNode(
        faq_store=general_sql_faq,
        guardrail_store=general_guardrail
    )

    general_sql_node = TreeNode(
        metadata={
            "product": "cmaap",
            "topic": "sql-migration"
        },
        leaf=general_leaf
    )

    # =========================================================
    # SSIS LEAF
    # =========================================================

    ssis_faq = VectorStore("ssis_faq")

    ssis_faq.add(
        "How do I migrate SSIS packages?",
        {
            "question": "How do I migrate SSIS packages?",
            "answer": "Convert SSIS workflows into Airflow or cloud ETL tools."
        }
    )

    ssis_guardrail = VectorStore("ssis_guardrail")

    ssis_guardrail.add(
        "delete production data",
        {
            "blocked_reason": "Dangerous operation"
        }
    )

    ssis_leaf = LeafNode(
        faq_store=ssis_faq,
        guardrail_store=ssis_guardrail
    )

    ssis_node = TreeNode(
        metadata={
            "product": "cmaap",
            "topic": "ssis-migration"
        },
        leaf=ssis_leaf
    )

    # =========================================================
    # CMAAP GENERAL LEAF
    # =========================================================

    cmaap_general_faq = VectorStore("cmaap_general_faq")

    cmaap_general_faq.add(
        "What is CMaaP?",
        {
            "question": "What is CMaaP?",
            "answer": "CMaaP is a SaaS platform for enterprise migration."
        }
    )

    cmaap_guardrail = VectorStore("cmaap_guardrail")

    cmaap_guardrail.add(
        "steal confidential data",
        {
            "blocked_reason": "Security threat"
        }
    )

    cmaap_leaf = LeafNode(
        faq_store=cmaap_general_faq,
        guardrail_store=cmaap_guardrail
    )

    cmaap_node = TreeNode(
        metadata={
            "product": "cmaap"
        },
        leaf=cmaap_leaf
    )

    # =========================================================
    # BUILD TREE
    # =========================================================

    sql_migration_node = TreeNode(
        metadata={
            "product": "cmaap",
            "topic": "sql-migration"
        },
        children=[
            tsql_node,
            teradata_node
        ],
        default_child=general_sql_node
    )

    root = TreeNode(
        metadata={
            "product": "cmaap"
        },
        children=[
            sql_migration_node,
            ssis_node
        ],
        default_child=cmaap_node
    )

    return RoutingTree(root)
# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Novuz CMaaP Retrieval API",
    version="1.0.0",
)


# =========================================================
# REQUEST MODEL
# =========================================================

class QueryRequest(BaseModel):
    query: str
    meta: dict


# =========================================================
# INITIALIZATION
# =========================================================

DATA_DIR = "./data"
TREE_PATH = os.path.join(DATA_DIR, "tree_structure.json")


def initialize_system():

    # Load existing tree
    if os.path.exists(TREE_PATH):

        print(f"📂 Loading existing routing tree from {DATA_DIR}...")

        tree = RoutingTree.load(DATA_DIR)

        print("✅ Tree loaded from disk")

    else:

        print("📦 Building routing tree from scratch...")

        tree = build_sample_tree()

        tree.save(DATA_DIR)

        print("✅ Tree created and saved")

    retriever = Retriever(
        tree=tree,
        k=5,
        theta_guard=0.85,
        theta_collapse=0.95,
        pick_threshold=0.3,
    )

    print("✅ Retriever initialized")

    return retriever


retriever = initialize_system()


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Novuz CMaaP Retrieval API Running"
    }


@app.post("/query")
def query_system(data: QueryRequest):

    try:

        # Run retrieval
        faqs = retriever.retrieve(
            data.query,
            data.meta
        )

        # Format context
        context = Retriever.format_context(faqs)

        return {
            "query": data.query,
            "meta": data.meta,
            "retrieved_faqs": faqs,
            "context": context,
            "status": "success"
        }

    except GuardrailException as e:

        raise HTTPException(
            status_code=403,
            detail=f"Guardrail violation: {str(e)}"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )