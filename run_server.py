from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from tree import RoutingTree, TreeNode, LeafNode
from retriever import Retriever, GuardrailException
from vector_store import VectorStore


# =========================================================
# APP
# =========================================================

app = FastAPI()


# =========================================================
# GLOBALS
# =========================================================

tree = None
retriever = None


# =========================================================
# STARTUP
# =========================================================

def load_tree():
    global tree
    global retriever

    tree = RoutingTree.load("./data")
    retriever = Retriever(tree)


try:
    load_tree()
    print("Tree loaded.")
except Exception as e:
    print(f"Startup warning: {e}")


# =========================================================
# REQUEST MODELS
# =========================================================

class QueryRequest(BaseModel):
    query: str
    query_meta: Dict[str, Any]
    k: int = 5


class PutLeafNodeRequest(BaseModel):
    metadata: Dict[str, Any]
    faq_store_name: str
    guardrail_store_name: str


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():
    return {"message": "FAQ API running"}


# =========================================================
# /query
# =========================================================

@app.post("/query")
async def query(req: QueryRequest):

    global retriever

    if retriever is None:
        raise HTTPException(status_code=500, detail="Retriever not loaded")

    try:
        retriever.k = req.k

        results = retriever.retrieve(
            req.query,
            req.query_meta
        )

        return {
            "query": req.query,
            "results": results
        }

    except GuardrailException as e:
        raise HTTPException(status_code=403, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# /tree_reload
# =========================================================

@app.post("/tree_reload")
async def tree_reload():

    global tree
    global retriever

    try:
        load_tree()

        return {
            "message": "Tree reloaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# /put_leafnode
# =========================================================

@app.post("/put_leafnode")
async def put_leafnode(req: PutLeafNodeRequest):

    global tree

    if tree is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")

    try:

        faq_store = VectorStore(req.faq_store_name)
        guardrail_store = VectorStore(req.guardrail_store_name)

        leaf = LeafNode(
            faq_store=faq_store,
            guardrail_store=guardrail_store
        )

        node = TreeNode(
            metadata=req.metadata,
            leaf=leaf
        )

        tree.root.children.append(node)

        tree.save("./data")

        return {
            "message": "Leaf node added successfully",
            "metadata": req.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




if __name__ == "__main__":
   import os
   os.system("uvicorn run_server:app --reload")