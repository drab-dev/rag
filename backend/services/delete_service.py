"""Delete Service
Handles deletion of documents from both ChromaDB and the graph database.
"""
import sys
import os

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Dict, Any

from backend.db.chroma_db import get_chroma_db
from backend.db.graph_db import get_graph_db


def delete_document(doc_id: str) -> Dict[str, Any]:
    """Delete a document from ChromaDB and the graph.

    Args:
        doc_id: Document identifier

    Returns:
        Dictionary describing the deletion outcome.
    """
    try:
        chroma_db = get_chroma_db()
        graph_db = get_graph_db()

        chroma_deleted = chroma_db.delete_document(doc_id)

        # Delete from graph (including related edges and orphan entities)
        if graph_db.node_exists(doc_id):
            graph_deleted = graph_db.delete_document_node(doc_id)
            # Persist graph after structural changes
            if graph_deleted:
                graph_db.save_graph()
        else:
            # Nothing to delete from graph, but that's fine
            graph_deleted = True

        success = chroma_deleted and graph_deleted

        return {
            "success": success,
            "doc_id": doc_id,
            "chroma_deleted": chroma_deleted,
            "graph_deleted": graph_deleted,
        }

    except Exception as e:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": str(e),
        }
