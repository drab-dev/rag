"""
Document Ingestion Service
Handles document ingestion pipeline including embedding generation,
storage in ChromaDB, entity extraction, and graph building
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Dict, List, Optional, Any

from models.embedding_model import generate_embedding
from backend.db.chroma_db import get_chroma_db
from backend.db.graph_db import get_graph_db
from backend.services.entity_extractor import extract_entities_spacy


def ingest_document(
    doc_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Ingest a document into the system
    
    Pipeline:
    1. Generate embedding
    2. Store in ChromaDB
    3. Extract entities
    4. Build graph relationships
    5. Persist graph
    
    Args:
        doc_id: Unique document identifier
        text: Document text content
        metadata: Optional metadata dictionary
        
    Returns:
        Dictionary with ingestion results
    """
    try:
        # Step 1: Generate embedding
        embedding = generate_embedding(text)
        
        # Step 2: Store in ChromaDB
        chroma_db = get_chroma_db()
        chroma_success = chroma_db.add_document_to_chroma(
            doc_id=doc_id,
            text=text,
            embedding=embedding,
            metadata=metadata,
        )
        
        if not chroma_success:
            return {
                "success": False,
                "error": "Failed to store document in ChromaDB"
            }
        
        # Step 3: Extract entities using spaCy noun-phrase extractor
        entities = extract_entities_spacy(text)
        
        # Step 4: Build graph
        graph_db = get_graph_db()
        
        # Add document node
        graph_db.add_document_node(doc_id)
        
        # Add entity nodes and edges
        for entity in entities:
            graph_db.add_entity_node(entity)
            graph_db.add_edge_between(doc_id, entity)
        
        # Step 5: Persist graph
        graph_success = graph_db.save_graph()
        
        if not graph_success:
            print("Warning: Failed to persist graph to disk")
        
        # Return success
        return {
            "success": True,
            "doc_id": doc_id,
            "entities_extracted": len(entities),
            "entities": entities,
            "metadata": metadata or {},
            "embedding_dim": len(embedding)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def batch_ingest_documents(
    documents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Ingest multiple documents at once
    
    Args:
        documents: List of documents, each with doc_id, text, and optional metadata
        
    Returns:
        Dictionary with batch ingestion results
    """
    results = {
        "total": len(documents),
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    for doc in documents:
        doc_id = doc.get("doc_id")
        text = doc.get("text")
        metadata = doc.get("metadata")
        
        if not doc_id or not text:
            results["failed"] += 1
            results["details"].append({
                "doc_id": doc_id,
                "success": False,
                "error": "Missing doc_id or text"
            })
            continue
        
        result = ingest_document(doc_id, text, metadata)
        
        if result["success"]:
            results["successful"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append(result)
    
    return results
