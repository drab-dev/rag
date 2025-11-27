"""
FastAPI Application - Hybrid Vector + Graph AI Retrieval Engine
Main application with REST API endpoints
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time

from backend.services.ingest_service import ingest_document, batch_ingest_documents
from backend.services.search_service import semantic_search, search_by_document_id
from backend.services.hybrid_service import hybrid_search, graph_neighbors, get_document_relationships
from backend.services.delete_service import delete_document as delete_document_service
from backend.db.graph_db import get_graph_db
from backend.db.chroma_db import get_chroma_db


# Pydantic models for request/response validation
class DocumentRequest(BaseModel):
    doc_id: str = Field(..., description="Unique document identifier")
    text: str = Field(..., description="Document text content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class BatchDocumentRequest(BaseModel):
    documents: List[DocumentRequest] = Field(..., description="List of documents to ingest")


# Initialize FastAPI app
app = FastAPI(
    title="Hybrid Vector + Graph AI Retrieval Engine",
    description="Backend system combining semantic search (ChromaDB) with graph reasoning (NetworkX)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Hybrid Vector + Graph AI Retrieval Engine",
        "version": "1.0.0",
        "endpoints": {
            "POST /add_document": "Ingest a new document",
            "POST /add_documents": "Batch ingest multiple documents",
            "GET /search": "Semantic vector search",
            "GET /hybrid": "Hybrid search (vector + graph)",
            "GET /graph_neighbors": "Get graph neighbors for a document",
            "GET /document/{doc_id}": "Retrieve a specific document",
            "DELETE /document/{doc_id}": "Delete a specific document",
            "GET /relationships/{doc_id}": "Get document relationships",
            "GET /stats": "Get system statistics",
            "GET /list_documents": "List all stored document IDs",
        }
    }


@app.post("/add_document")
async def add_document(doc_request: DocumentRequest):
    """
    Ingest a new document into the system
    
    Process:
    1. Generate embedding
    2. Store in ChromaDB
    3. Extract entities
    4. Build graph relationships
    """
    result = ingest_document(
        doc_id=doc_request.doc_id,
        text=doc_request.text,
        metadata=doc_request.metadata
    )
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Ingestion failed"))


@app.post("/add_documents")
async def add_documents(batch_request: BatchDocumentRequest):
    """
    Batch ingest multiple documents
    """
    documents = [doc.dict() for doc in batch_request.documents]
    result = batch_ingest_documents(documents)
    return result


@app.get("/search")
async def search(
    q: str = Query(..., description="Search query text"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return")
):
    """
    Perform semantic vector search
    
    Args:
        q: Query text
        top_k: Number of results (1-50)
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    result = semantic_search(query=q, top_k=top_k)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))


@app.get("/hybrid")
async def hybrid(
    q: str = Query(..., description="Search query text"),
    top_k: int = Query(5, ge=1, le=20, description="Number of initial vector results"),
    depth: int = Query(1, ge=1, le=3, description="Graph traversal depth")
):
    """
    Perform hybrid search combining vector search and graph traversal
    
    Args:
        q: Query text
        top_k: Number of initial vector search results (1-20)
        depth: Graph traversal depth (1-3)
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    result = hybrid_search(query=q, top_k=top_k, graph_depth=depth)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Hybrid search failed"))


@app.get("/graph_neighbors")
async def get_graph_neighbors(
    doc_id: str = Query(..., description="Document identifier"),
    depth: int = Query(1, ge=1, le=3, description="Maximum traversal depth")
):
    """
    Get graph neighbors for a specific document
    
    Args:
        doc_id: Document identifier
        depth: Maximum traversal depth (1-3)
    """
    result = graph_neighbors(doc_id=doc_id, depth=depth)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=404, detail=result.get("error", "Document not found"))


@app.get("/document/{doc_id}")
async def get_document(doc_id: str):
    """
    Retrieve a specific document by ID
    
    Args:
        doc_id: Document identifier
    """
    result = search_by_document_id(doc_id)
    
    if result["success"] and result["found"]:
        return result
    elif result["success"] and not result["found"]:
        raise HTTPException(status_code=404, detail="Document not found")
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Retrieval failed"))


@app.get("/relationships/{doc_id}")
async def get_relationships(doc_id: str):
    """
    Get detailed relationship information for a document
    
    Args:
        doc_id: Document identifier
    """
    result = get_document_relationships(doc_id)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=404, detail=result.get("error", "Document not found"))


@app.delete("/document/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a specific document from both ChromaDB and the graph."""
    result = delete_document_service(doc_id)

    if result["success"]:
        return result

    # If both backends report no deletion, treat as not found; otherwise 500.
    chroma_deleted = result.get("chroma_deleted")
    graph_deleted = result.get("graph_deleted")

    if chroma_deleted is False and graph_deleted is False:
        raise HTTPException(status_code=404, detail="Document not found")

    raise HTTPException(status_code=500, detail=result.get("error", "Deletion failed"))


@app.get("/list_documents")
async def list_documents():
    """Return a list of all stored document IDs from ChromaDB."""
    try:
        chroma_db = get_chroma_db()
        doc_ids = chroma_db.list_document_ids()
        return {
            "success": True,
            "count": len(doc_ids),
            "documents": doc_ids,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


# Simple in-process cache for expensive /stats computation.
# This does NOT change how often clients can hit /stats, but limits
# how often we actually touch ChromaDB and the graph. Adjust TTL
# (in seconds) as needed, e.g. 5.0 or 10.0.
_STATS_CACHE: Optional[Dict[str, Any]] = None
_STATS_CACHE_LAST: float = 0.0
_STATS_CACHE_TTL: float = 5.0  # seconds


@app.get("/stats")
async def get_stats():
    """Get system statistics with simple caching.

    To avoid hammering the database/graph when /stats is polled very
    frequently (e.g., by a dashboard), we cache the result for a short
    TTL and return the cached value until it expires.
    """
    global _STATS_CACHE, _STATS_CACHE_LAST

    now = time.time()
    if _STATS_CACHE is not None and (now - _STATS_CACHE_LAST) < _STATS_CACHE_TTL:
        return _STATS_CACHE

    try:
        graph_db = get_graph_db()
        chroma_db = get_chroma_db()

        graph_stats = graph_db.get_graph_stats()
        chroma_count = chroma_db.count_documents()

        result = {
            "success": True,
            "chromadb": {
                "total_documents": chroma_count
            },
            "graph": graph_stats,
            "system": {
                "status": "operational"
            }
        }

        _STATS_CACHE = result
        _STATS_CACHE_LAST = now

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Hybrid Vector + Graph AI Retrieval Engine"
    }


if __name__ == "__main__":
    import multiprocessing
    import uvicorn
    
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
