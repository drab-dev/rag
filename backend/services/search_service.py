"""
Search Service
Handles semantic search operations using vector embeddings
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Dict, List, Any
from models.embedding_model import generate_embedding
from backend.db.chroma_db import get_chroma_db


def semantic_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Perform semantic search using query embedding
    
    Args:
        query: Search query text
        top_k: Number of results to return
        
    Returns:
        Dictionary containing search results with doc_ids, documents, metadata, and distances
    """
    try:
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Perform search in ChromaDB
        chroma_db = get_chroma_db()
        results = chroma_db.semantic_search(
            query_embedding=query_embedding,
            top_k=top_k
        )
        
        # Format results for better readability
        formatted_results = []
        for i in range(len(results["doc_ids"])):
            formatted_results.append({
                "doc_id": results["doc_ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i],
                "distance": results["distances"][i],
                "relevance_score": 1 - results["distances"][i]  # Convert distance to similarity
            })
        
        return {
            "success": True,
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "results_count": 0,
            "results": []
        }


def search_by_document_id(doc_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific document by its ID
    
    Args:
        doc_id: Document identifier
        
    Returns:
        Dictionary containing document data
    """
    try:
        chroma_db = get_chroma_db()
        document = chroma_db.get_document(doc_id)
        
        if document:
            return {
                "success": True,
                "found": True,
                "doc_id": doc_id,
                "document": document["document"],
                "metadata": document["metadata"]
            }
        else:
            return {
                "success": True,
                "found": False,
                "doc_id": doc_id,
                "message": "Document not found"
            }
            
    except Exception as e:
        return {
            "success": False,
            "found": False,
            "doc_id": doc_id,
            "error": str(e)
        }


def get_similar_documents(doc_id: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Find documents similar to a given document
    
    Args:
        doc_id: Document identifier
        top_k: Number of similar documents to return
        
    Returns:
        Dictionary containing similar documents
    """
    try:
        # Get the source document
        chroma_db = get_chroma_db()
        source_doc = chroma_db.get_document(doc_id)
        
        if not source_doc or not source_doc.get("embedding"):
            return {
                "success": False,
                "error": "Document not found or has no embedding",
                "results_count": 0,
                "results": []
            }
        
        # Use the document's embedding to find similar documents
        results = chroma_db.semantic_search(
            query_embedding=source_doc["embedding"],
            top_k=top_k + 1  # +1 because the source document will be in results
        )
        
        # Filter out the source document itself
        formatted_results = []
        for i in range(len(results["doc_ids"])):
            if results["doc_ids"][i] != doc_id:
                formatted_results.append({
                    "doc_id": results["doc_ids"][i],
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "distance": results["distances"][i],
                    "relevance_score": 1 - results["distances"][i]
                })
        
        # Limit to top_k results
        formatted_results = formatted_results[:top_k]
        
        return {
            "success": True,
            "source_doc_id": doc_id,
            "results_count": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "source_doc_id": doc_id,
            "error": str(e),
            "results_count": 0,
            "results": []
        }
