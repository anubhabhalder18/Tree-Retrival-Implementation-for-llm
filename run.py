"""run.py

API-style entrypoint using Pydantic models for tree construction, routing,
retrieval, and FAQ response generation.

This script builds the routing tree from leaf configurations using explicit
metadata ordering, persists the tree and store contents to JSON, and exposes
an API-style query function that validates input with Pydantic.
"""

import json
import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError

from retriever import GuardrailException, Retriever
from tree import LeafNode, RoutingTree, TreeNode
from vector_store import VectorStore

DEFAULT_DATA_DIR = "./data"
DEFAULT_METADATA_KEY_ORDER = ["product", "topic", "dialect"]


class FAQEntry(BaseModel):
    question: str
    answer: str


class GuardrailEntry(BaseModel):
    text: str
    blocked_reason: str = Field(default="Blocked by guardrail")


class LeafConfig(BaseModel):
    metadata: Dict[str, str]
    faqs: List[FAQEntry]
    guardrails: List[GuardrailEntry] = Field(default_factory=list)


class QueryRequest(BaseModel):
    query: str
    metadata: Dict[str, str]
    k: int = Field(default=5, ge=1)
    theta_guard: float = Field(default=0.85, ge=0.0, le=1.0)
    theta_collapse: float = Field(default=0.95, ge=0.0, le=1.0)
    pick_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    query: str
    metadata: Dict[str, str]
    routed_leaf_metadata: Dict[str, Any]
    retrieved_faqs: List[Dict[str, Any]]


def _store_name_from_metadata(metadata: Dict[str, str], suffix: str) -> str:
    ordered_items = [f"{k}-{metadata[k]}" for k in DEFAULT_METADATA_KEY_ORDER if k in metadata]
    if not ordered_items:
        ordered_items = ["default"]
    safe_name = "_".join(ordered_items).replace(" ", "_").lower()
    return f"{safe_name}_{suffix}"


def _insert_leaf(root: TreeNode, leaf_node: LeafNode, metadata: Dict[str, str]) -> None:
    current = root
    for key in DEFAULT_METADATA_KEY_ORDER:
        if key not in metadata:
            break

        child_meta = {key: metadata[key]}
        matching_child = next((child for child in current.children if child.metadata == child_meta), None)
        if matching_child is None:
            matching_child = TreeNode(metadata=child_meta)
            current.children.append(matching_child)
        current = matching_child

    if current.is_leaf():
        if current.default_child is None:
            current.default_child = TreeNode(metadata={}, leaf=leaf_node)
        else:
            raise ValueError(f"Cannot insert leaf: path conflict for metadata {metadata}")
    elif current.leaf is None and not current.children:
        current.leaf = leaf_node
    else:
        if current.leaf is None:
            current.default_child = TreeNode(metadata={}, leaf=leaf_node)
        else:
            current.default_child = TreeNode(metadata={}, leaf=leaf_node)


def build_routing_tree(leaf_configs: List[LeafConfig]) -> RoutingTree:
    root = TreeNode(metadata={})
    for leaf_config in leaf_configs:
        faq_store_name = _store_name_from_metadata(leaf_config.metadata, "faq")
        guardrail_store_name = _store_name_from_metadata(leaf_config.metadata, "guardrail")

        faq_store = VectorStore(faq_store_name)
        for faq in leaf_config.faqs:
            faq_store.add(faq.question, faq.dict())

        guardrail_store = VectorStore(guardrail_store_name)
        for guardrail in leaf_config.guardrails:
            guardrail_store.add(guardrail.text, {"blocked_reason": guardrail.blocked_reason})

        leaf_node = LeafNode(faq_store=faq_store, guardrail_store=guardrail_store)
        _insert_leaf(root, leaf_node, leaf_config.metadata)

    return RoutingTree(root)


def find_routed_metadata(node: TreeNode, query_meta: Dict[str, str]) -> Dict[str, Any]:
    if node.is_leaf():
        return node.metadata

    for child in node.children:
        if TreeNode._matches(query_meta, child.metadata):
            return find_routed_metadata(child, query_meta)

    if node.default_child is not None:
        return find_routed_metadata(node.default_child, query_meta)

    return node.metadata


def load_or_build_tree(data_dir: str = DEFAULT_DATA_DIR) -> RoutingTree:
    if os.path.exists(os.path.join(data_dir, "tree_structure.json")):
        return RoutingTree.load(data_dir)

    leaf_configs = [
        LeafConfig(
            metadata={"product": "cmaap", "topic": "sql-migration", "dialect": "tsql"},
            faqs=[
                FAQEntry(question="How do I convert SQL Server CAST to standard SQL?", answer="Use CAST() function which is standard SQL-92. Example: CAST(column AS VARCHAR(10))"),
                FAQEntry(question="What's the difference between GETDATE() and SYSDATETIME()?", answer="GETDATE() returns DATETIME, SYSDATETIME() returns DATETIME2. Use SYSDATETIME() for better precision."),
                FAQEntry(question="How do I handle T-SQL specific data types?", answer="T-SQL specific types: UNIQUEIDENTIFIER -> UUID, NVARCHAR -> VARCHAR with UTF-8 collation, TEXT -> CLOB"),
            ],
            guardrails=[
                GuardrailEntry(text="hacking attacks SQL injection", blocked_reason="Security threat"),
                GuardrailEntry(text="drop table production", blocked_reason="Dangerous operation"),
            ],
        ),
        LeafConfig(
            metadata={"product": "cmaap", "topic": "sql-migration", "dialect": "teradata"},
            faqs=[
                FAQEntry(question="How do I convert Teradata CAST functions?", answer="Teradata CAST is similar to standard SQL. Main difference: CAST(col AS CHAR(10)) vs CAST(col AS VARCHAR(10))"),
                FAQEntry(question="What about Teradata temporal tables?", answer="Teradata uses VERSIONING clause. Convert to standard SQL temporal tables or maintain version history in separate tables."),
                FAQEntry(question="How do I handle Teradata specific functions?", answer="CURRENT_TIMESTAMP works in both. For Teradata specifics: EXTRACT, SUBSTR, CAST all have standard SQL equivalents."),
            ],
            guardrails=[
                GuardrailEntry(text="terminate database", blocked_reason="Dangerous operation"),
                GuardrailEntry(text="malicious code execution", blocked_reason="Security threat"),
            ],
        ),
        LeafConfig(
            metadata={"product": "cmaap", "topic": "sql-migration"},
            faqs=[
                FAQEntry(question="What's the migration process for SQL dialects?", answer="1. Analyze source schema and queries, 2. Map data types, 3. Convert dialect-specific functions, 4. Test thoroughly"),
                FAQEntry(question="How do I handle stored procedures across dialects?", answer="Extract business logic, convert syntax, test with sample data. Consider refactoring complex procedures."),
                FAQEntry(question="What are common migration pitfalls?", answer="Implicit type conversions, date/time handling, NULL semantics, and performance regression. Plan thorough testing."),
            ],
            guardrails=[
                GuardrailEntry(text="unauthorized access database", blocked_reason="Security threat"),
            ],
        ),
        LeafConfig(
            metadata={"product": "cmaap", "topic": "ssis-migration"},
            faqs=[
                FAQEntry(question="How do I migrate SSIS packages?", answer="Convert SSIS to Apache Airflow, Talend, or cloud ETL tools. Extract control flow and data flow logic."),
                FAQEntry(question="What about SSIS transformations?", answer="SSIS transformations map to Python/SQL equivalents. Use pandas for data transformation or SQL transformations."),
                FAQEntry(question="How do I test SSIS migrations?", answer="Validate data quality, compare row counts, test error handling, verify performance on representative data volumes."),
            ],
            guardrails=[
                GuardrailEntry(text="delete production data", blocked_reason="Dangerous operation"),
            ],
        ),
        LeafConfig(
            metadata={"product": "cmaap"},
            faqs=[
                FAQEntry(question="What is CMaaP?", answer="CMaaP (Continuous Modernization as a Product) is Novuz's SaaS platform for enterprise data warehouse migration."),
                FAQEntry(question="What databases does CMaaP support?", answer="CMaaP supports SQL Server (T-SQL), Teradata, Snowflake, BigQuery, Redshift, and other modern data warehouses."),
                FAQEntry(question="How do I get started with CMaaP?", answer="1. Create account, 2. Connect source database, 3. Analyze schema, 4. Configure migration rules, 5. Test and deploy."),
            ],
            guardrails=[
                GuardrailEntry(text="delete customer database", blocked_reason="Dangerous operation"),
                GuardrailEntry(text="steal data confidential", blocked_reason="Security threat"),
            ],
        ),
    ]

    tree = build_routing_tree(leaf_configs)
    tree.save(data_dir)
    return tree


def run_query_api(request_data: Dict[str, Any], tree: RoutingTree) -> QueryResponse:
    request = QueryRequest.parse_obj(request_data)

    retriever = Retriever(
        tree=tree,
        k=request.k,
        theta_guard=request.theta_guard,
        theta_collapse=request.theta_collapse,
        pick_threshold=request.pick_threshold,
    )

    faqs = retriever.retrieve(request.query, request.metadata)
    routed_leaf_metadata = find_routed_metadata(tree.root, request.metadata)

    return QueryResponse(
        query=request.query,
        metadata=request.metadata,
        routed_leaf_metadata=routed_leaf_metadata,
        retrieved_faqs=faqs,
    )


def main() -> None:
    tree = load_or_build_tree(DEFAULT_DATA_DIR)
    sample_request = {
        "query": "How do I convert SQL Server CAST functions to be compatible with Teradata?",
        "metadata": {"product": "cmaap", "topic": "sql-migration", "dialect": "tsql"},
    }

    try:
        response = run_query_api(sample_request, tree)
        print(response.json(indent=2))
    except GuardrailException as exc:
        print(f"Guardrail violation: {exc}")
    except ValidationError as exc:
        print(f"Request validation failed:\n{exc}")


if __name__ == "__main__":
    main()
