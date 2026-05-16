from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
import json
import os

from vector_store import VectorStore


@dataclass
class LeafNode:
    faq_store: VectorStore
    guardrail_store: VectorStore

    def to_dict(self) -> dict:
        """Convert leaf node to a serializable dictionary."""
        return {
            "faq_store_name": self.faq_store.name,
            "guardrail_store_name": self.guardrail_store.name
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional[LeafNode]:
        
        if not data:
            return None
        
        return cls(
            faq_store=VectorStore(data["faq_store_name"]),
            guardrail_store=VectorStore(data["guardrail_store_name"])
        )


@dataclass
class TreeNode:
   
    metadata: dict[str, Any]
    children: list[TreeNode] = field(default_factory=list)
    default_child: Optional[TreeNode] = None
    leaf: Optional[LeafNode] = None

    def is_leaf(self) -> bool:
       
        return self.leaf is not None

    def route(self, query_meta: dict[str, Any]) -> TreeNode:
        
        
        if self.is_leaf():
            return self

        for child in self.children:
            if self._matches(query_meta, child.metadata):
                return child.route(query_meta)

        if self.default_child is not None:
            return self.default_child.route(query_meta)

        return self

    @staticmethod
    def _matches(query_meta: dict[str, Any], node_meta: dict[str, Any]) -> bool:
        
        for key, value in node_meta.items():
            if query_meta.get(key) != value:
                return False
        return True

    def to_dict(self) -> dict:
        
        return {
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
            "default_child": self.default_child.to_dict() if self.default_child else None,
            "leaf": self.leaf.to_dict() if self.leaf else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional[TreeNode]:
        
        if not data:
            return None
        
        return cls(
            metadata=data.get("metadata", {}),
            children=[cls.from_dict(c) for c in data.get("children", [])],
            default_child=cls.from_dict(data["default_child"]) if data.get("default_child") else None,
            leaf=LeafNode.from_dict(data["leaf"]) if data.get("leaf") else None
        )


class RoutingTree:
    

    def __init__(self, root: TreeNode):
        

        self.root = root

    def traverse(self, query_meta: dict[str, Any]) -> LeafNode:
        
        result = self.root.route(query_meta)

        if not result.is_leaf():
            raise ValueError(
                f"Traversal failed to reach a leaf node. Ended at node with metadata: {result.metadata}"
            )

        return result.leaf

    def save(self, directory: str = "./data") -> None:
        
        os.makedirs(directory, exist_ok=True)
        
   
        def _save_stores(node: TreeNode):
            if node.leaf:
                node.leaf.faq_store.save(directory)
                node.leaf.guardrail_store.save(directory)
            for child in node.children:
                _save_stores(child)
            if node.default_child:
                _save_stores(node.default_child)
        
        _save_stores(self.root)
        
      
        structure = self.root.to_dict()
        with open(os.path.join(directory, "tree_structure.json"), "w", encoding="utf-8") as f:
            json.dump(structure, f, indent=2)

    @classmethod
    def load(cls, directory: str = "./data") -> RoutingTree:
        

        path = os.path.join(directory, "tree_structure.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Tree structure not found at {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        root = TreeNode.from_dict(data)
        tree = cls(root)
        
        def _load_stores(node: TreeNode):
            if node.leaf:
                node.leaf.faq_store.load(directory)
                node.leaf.guardrail_store.load(directory)
            for child in node.children:
                _load_stores(child)
            if node.default_child:
                _load_stores(node.default_child)
                
        _load_stores(tree.root)
        return tree
    