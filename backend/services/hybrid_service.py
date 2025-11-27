"""
Hybrid Search Service
Combines semantic vector search with graph-based relationship reasoning
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Dict, List, Any, Set
from backend.services.search_service import semantic_search
from backend.db.graph_db import get_graph_db
from backend.db.chroma_db import get_chroma_db
from backend.services.ai_relation_service import analyze_document_relationships
from models.llm_client import is_llm_configured

def _normalize_scores(raw_scores: Dict[str, float]) -> Dict[str, float]:
    """Min-max normalise a mapping of id -> score into [0, 1]."""
    if not raw_scores:
        return {}

    values = list(raw_scores.values())
    max_v = max(values)
    min_v = min(values)

    if max_v == min_v:
        # All equal; if non-zero, treat them all as 1.0, else 0.0
        return {k: (1.0 if max_v > 0 else 0.0) for k in raw_scores}

    span = max_v - min_v
    return {k: (v - min_v) / span for k, v in raw_scores.items()}

def hybrid_search(query: str, top_k: int = 5, graph_depth: int = 2) -> Dict[str, Any]:
    """Perform true hybrid search combining vector similarity + graph expansion.

    Pipeline:
    1. Run semantic vector search against ChromaDB.
    2. For each top vector hit, find graph-connected documents via shared entities.
    3. Compute separate vector and graph scores per document.
    4. Combine scores into a single hybrid score and rank.

    Args:
        query: Search query text.
        top_k: Number of initial semantic search results.
        graph_depth: Logical graph depth parameter. The current graph is
            bipartite (document <-> entity). We treat depth >= 2 as allowing
            expansion from a document to its entities and to other documents
            connected through those entities.

    Returns:
        Dictionary with vector_hits, graph_expansion, and hybrid_results.
    """
    try:
        # --------------------------------------------------------------
        # STEP 1 — Vector search
        # --------------------------------------------------------------
        vector_results = semantic_search(query, top_k)

        if not vector_results["success"]:
            return {
                "success": False,
                "query": query,
                "error": vector_results.get("error", "Semantic search failed"),
                "vector_hits": [],
                "vector_hits_count": 0,
                "graph_expansion": [],
                "graph_expansion_count": 0,
                "entities": [],
                "entities_count": 0,
                "hybrid_results": [],
                "hybrid_results_count": 0,
            }

        graph_db = get_graph_db()
        chroma_db = get_chroma_db()

        # Map doc_id -> vector-result payload and raw vector score.
        vector_hits: Dict[str, Dict[str, Any]] = {}
        vector_scores_raw: Dict[str, float] = {}

        for res in vector_results["results"]:
            doc_id = res["doc_id"]
            # The semantic search already provides a relevance_score ~= 1 - distance.
            score = float(res.get("relevance_score") or 0.0)
            res_copy = res.copy()
            res_copy["vector_score"] = score
            # Mark as vector-only for now; may be upgraded to "vector+graph" later.
            res_copy["source"] = "vector_hit"
            vector_hits[doc_id] = res_copy
            vector_scores_raw[doc_id] = score

        # --------------------------------------------------------------
        # STEP 2 — Graph expansion via shared entities
        # --------------------------------------------------------------
        # We only perform meaningful expansion if depth >= 2 in this
        # bipartite (doc <-> entity) graph.
        graph_scores_raw: Dict[str, float] = {}
        entity_to_docs: Dict[str, Set[str]] = {}

        if graph_depth >= 2:
            for doc_id in vector_hits.keys():
                # Get entities attached to this document.
                entities = graph_db.get_document_entities(doc_id)

                for entity in entities:
                    related_docs = graph_db.get_related_documents(entity)
                    # Filter out the source document itself.
                    related_docs = [d for d in related_docs if d != doc_id]
                    if not related_docs:
                        continue

                    doc_set = entity_to_docs.setdefault(entity, set())
                    doc_set.update(related_docs)

                    # Use "number of shared entities" as a simple graph score.
                    for rel_doc in related_docs:
                        graph_scores_raw[rel_doc] = graph_scores_raw.get(rel_doc, 0.0) + 1.0

        # Build a compact entity info structure for the response (limited).
        entity_info: List[Dict[str, Any]] = []
        for entity, docs in list(entity_to_docs.items())[:20]:
            docs_list = sorted(docs)
            entity_info.append(
                {
                    "entity": entity,
                    "related_document_count": len(docs_list),
                    "related_documents": docs_list,
                }
            )

        # --------------------------------------------------------------
        # STEP 3 — Retrieve graph-expanded documents (graph_expansion)
        # --------------------------------------------------------------
        graph_expansion_results: List[Dict[str, Any]] = []
        graph_docs_payload: Dict[str, Dict[str, Any]] = {}

        for doc_id, g_score in graph_scores_raw.items():
            # Fetch document content from Chroma.
            doc_data = chroma_db.get_document(doc_id)
            if not doc_data:
                continue

            payload = {
                "doc_id": doc_id,
                "document": doc_data["document"],
                "metadata": doc_data["metadata"],
                "graph_score": g_score,
                "source": "graph_expansion",
            }
            graph_docs_payload[doc_id] = payload

            # Only include *new* docs (not already top vector hits) in
            # the explicit graph_expansion list, to avoid duplication.
            if doc_id not in vector_hits:
                graph_expansion_results.append(payload)

        # --------------------------------------------------------------
        # STEP 4 — Combined ranking (vector + graph)
        # --------------------------------------------------------------
        vector_scores_norm = _normalize_scores(vector_scores_raw)
        graph_scores_norm = _normalize_scores(graph_scores_raw)

        hybrid_results: List[Dict[str, Any]] = []
        all_doc_ids = set(vector_hits.keys()) | set(graph_docs_payload.keys())

        for doc_id in all_doc_ids:
            v_raw = vector_scores_raw.get(doc_id, 0.0)
            v_norm = vector_scores_norm.get(doc_id, 0.0)
            g_raw = graph_scores_raw.get(doc_id, 0.0)
            g_norm = graph_scores_norm.get(doc_id, 0.0)

            # Weighted combination; weights can be tuned.
            final_score = 0.7 * v_norm + 0.3 * g_norm

            if doc_id in vector_hits:
                base = vector_hits[doc_id].copy()
            else:
                base = graph_docs_payload[doc_id].copy()

            # Explanation/source label.
            if doc_id in vector_hits and doc_id in graph_docs_payload:
                source = "vector+graph"
            elif doc_id in vector_hits:
                source = "vector_hit"
            else:
                source = "graph_expansion"

            base.update(
                {
                    "source": source,
                    # Final hybrid score is exposed as relevance_score so the
                    # frontend can display it consistently.
                    "relevance_score": final_score,
                    "vector_score": v_raw,
                    "vector_score_normalized": v_norm,
                    "graph_score": g_raw,
                    "graph_score_normalized": g_norm,
                }
            )

            hybrid_results.append(base)

        # Sort by final hybrid score (descending)
        hybrid_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        # Vector hits list for the response (keep original order, but annotate
        # with source + scores for transparency).
        ordered_vector_hits: List[Dict[str, Any]] = []
        for res in vector_results["results"]:
            doc_id = res["doc_id"]
            annotated = vector_hits[doc_id].copy()
            annotated["graph_score"] = graph_scores_raw.get(doc_id, 0.0)
            annotated["graph_score_normalized"] = graph_scores_norm.get(doc_id, 0.0)
            ordered_vector_hits.append(annotated)

        return {
            "success": True,
            "query": query,
            "vector_hits": ordered_vector_hits,
            "vector_hits_count": len(ordered_vector_hits),
            "graph_expansion": graph_expansion_results,
            "graph_expansion_count": len(graph_expansion_results),
            "entities": entity_info,
            "entities_count": len(entity_info),
            "hybrid_results": hybrid_results,
            "hybrid_results_count": len(hybrid_results),
        }

    except Exception as e:
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "vector_hits": [],
            "vector_hits_count": 0,
            "graph_expansion": [],
            "graph_expansion_count": 0,
            "entities": [],
            "entities_count": 0,
            "hybrid_results": [],
            "hybrid_results_count": 0,
        }


def graph_neighbors(doc_id: str, depth: int = 1) -> Dict[str, Any]:
    """
    Get graph neighbors for a specific document
    
    Args:
        doc_id: Document identifier
        depth: Maximum traversal depth
        
    Returns:
        Dictionary with neighbor information
    """
    try:
        graph_db = get_graph_db()
        
        # Check if document exists
        if not graph_db.node_exists(doc_id):
            return {
                "success": False,
                "doc_id": doc_id,
                "error": "Document not found in graph",
                "neighbors": []
            }
        
        # Get neighbors
        neighbors = graph_db.get_neighbors(doc_id, depth=depth)
        
        # Categorize neighbors
        document_neighbors = []
        entity_neighbors = []
        
        for neighbor in neighbors:
            node_attrs = graph_db.get_node_attributes(neighbor)
            neighbor_info = {
                "node_id": neighbor,
                "node_type": node_attrs.get("node_type", "unknown")
            }
            
            if node_attrs.get("node_type") == "document":
                document_neighbors.append(neighbor_info)
            elif node_attrs.get("node_type") == "entity":
                entity_neighbors.append(neighbor_info)
        
        return {
            "success": True,
            "doc_id": doc_id,
            "depth": depth,
            "total_neighbors": len(neighbors),
            "document_neighbors": document_neighbors,
            "document_neighbors_count": len(document_neighbors),
            "entity_neighbors": entity_neighbors,
            "entity_neighbors_count": len(entity_neighbors),
            "all_neighbors": neighbors
        }
        
    except Exception as e:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": str(e),
            "neighbors": []
        }


def get_document_relationships(doc_id: str) -> Dict[str, Any]:
    """Get detailed relationship information for a document.

    This function now prefers an AI-based implementation (using the Groq LLM)
    when available, with a graceful fallback to the legacy graph-based logic.

    Args:
        doc_id: Document identifier

    Returns:
        Dictionary with relationship details compatible with the existing
        frontend contract.
    """
    # First, try the AI-powered implementation if the LLM is configured.
    if is_llm_configured():
        try:
            ai_result = analyze_document_relationships(doc_id)
            if ai_result.get("success"):
                return ai_result
        except Exception:
            # If anything goes wrong with the AI layer, fall back silently to
            # the graph-based implementation below.
            pass

    # Legacy graph-based behavior (exact entity string matching).
    try:
        graph_db = get_graph_db()

        if not graph_db.node_exists(doc_id):
            return {
                "success": False,
                "doc_id": doc_id,
                "error": "Document not found in graph",
            }

        # Get entities connected to this document
        entities = graph_db.get_document_entities(doc_id)

        # For each entity, find related documents
        related_via_entities = {}
        all_related_docs = set()

        for entity in entities:
            related_docs = graph_db.get_related_documents(entity)
            # Filter out the source document itself
            related_docs = [doc for doc in related_docs if doc != doc_id]
            related_via_entities[entity] = related_docs
            all_related_docs.update(related_docs)

        return {
            "success": True,
            "doc_id": doc_id,
            "entities": entities,
            "entities_count": len(entities),
            "related_via_entities": related_via_entities,
            "related_documents": list(all_related_docs),
            "related_documents_count": len(all_related_docs),
        }

    except Exception as e:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": str(e),
        }
