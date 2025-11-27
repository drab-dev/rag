"""AI Relation Service

Uses the Groq-backed LLM client to perform cross-document entity linking and
relation extraction for a given document ID. This is used to power the
`/relationships/{doc_id}` endpoint when the LLM is available.

The service:
- Fetches the focus document from ChromaDB.
- Gathers a small set of candidate related documents from the existing graph
  and from semantic similarity.
- Sends these to the LLM with instructions to:
  * Normalize entities across documents (cross-document entity linking).
  * Extract relationships between entities.
- Adapts the LLM output to the shape expected by the frontend:
  * `entities`: list of canonical entity IDs.
  * `related_via_entities`: mapping entity -> list of related doc_ids.
  * `related_documents`: union of related doc_ids.

If anything fails (LLM not configured, prompt too big, JSON parse issues),
callers should fall back to the legacy graph-based implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set
import json

from backend.db.chroma_db import get_chroma_db
from backend.db.graph_db import get_graph_db
from backend.services.search_service import get_similar_documents
from models.llm_client import call_llm_for_json


_MAX_FOCUS_CHARS = 3000
_MAX_RELATED_DOCS = 8
_MAX_RELATED_CHARS = 1500


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def analyze_document_relationships(doc_id: str) -> Dict[str, Any]:
    """Run AI-based cross-document entity linking and relation extraction.

    Returns a dict with at minimum:
    - success: bool
    - doc_id: str
    - entities: List[str]
    - entities_count: int
    - related_via_entities: Dict[str, List[str]]
    - related_documents: List[str]
    - related_documents_count: int

    Additional AI-specific fields may be included, such as `ai_entities`
    and `ai_relations`, which the frontend can ignore until needed.
    """

    chroma_db = get_chroma_db()
    graph_db = get_graph_db()

    # 1) Fetch focus document
    focus_doc = chroma_db.get_document(doc_id)
    if not focus_doc or not focus_doc.get("document"):
        return {
            "success": False,
            "doc_id": doc_id,
            "error": "Document not found or has no text in ChromaDB",
        }

    focus_text = str(focus_doc["document"])

    # 2) Collect candidate related docs from graph via entities
    candidate_doc_ids: Set[str] = set()

    entities_from_graph = graph_db.get_document_entities(doc_id)
    for entity in entities_from_graph:
        for rel_doc in graph_db.get_related_documents(entity):
            if rel_doc != doc_id:
                candidate_doc_ids.add(rel_doc)

    # 3) Augment with semantic neighbors (if any)
    try:
        similar = get_similar_documents(doc_id, top_k=5)
        if similar.get("success"):
            for item in similar.get("results", []):
                rel_id = item.get("doc_id")
                if rel_id and rel_id != doc_id:
                    candidate_doc_ids.add(rel_id)
    except Exception:
        # If semantic similarity fails, we still proceed with graph-based candidates.
        pass

    # 4) Fetch related documents (capped)
    related_docs_payload: List[Dict[str, Any]] = []
    for rel_id in list(candidate_doc_ids)[:_MAX_RELATED_DOCS]:
        d = chroma_db.get_document(rel_id)
        if not d or not d.get("document"):
            continue
        related_docs_payload.append(
            {
                "doc_id": rel_id,
                "text": _truncate(str(d["document"]), _MAX_RELATED_CHARS),
            }
        )

    # If there are no candidates at all, we can short-circuit to an empty
    # but successful structure.
    if not related_docs_payload:
        return {
            "success": True,
            "doc_id": doc_id,
            "entities": [],
            "entities_count": 0,
            "related_via_entities": {},
            "related_documents": [],
            "related_documents_count": 0,
            "ai_entities": [],
            "ai_relations": [],
        }

    # 5) Build LLM input
    llm_input = {
        "focus_document": {
            "doc_id": doc_id,
            "text": _truncate(focus_text, _MAX_FOCUS_CHARS),
        },
        "related_documents": related_docs_payload,
    }

    system_prompt = (
        "You are an expert information extraction engine. Given a focus document "
        "and a small set of related documents, you must perform (1) cross-document "
        "entity resolution and (2) relation extraction between entities.\n\n"
        "Cross-document entity resolution: identify real-world entities that may be "
        "mentioned with slightly different surface forms (e.g. 'OpenAI', 'OpenAI, Inc.', "
        "'the company OpenAI'). Map all such mentions to a single canonical entity id.\n\n"
        "Relation extraction: infer meaningful relationships between entities across "
        "documents (e.g. WORKS_FOR, FOUNDED, LOCATED_IN, ACQUIRED, PART_OF). If no "
        "clear relation exists, you may omit it.\n\n"
        "Focus on high-precision entities and relations; do NOT invent facts that are "
        "not clearly supported by the text."
    )

    user_content = (
        "You are given JSON with a focus document and a small list of related "
        "documents. Extract canonical entities and relations. Use this exact JSON "
        "schema in your reply:\n\n"
        "{\n"
        "  \"entities\": [\n"
        "    {\n"
        "      \"id\": \"string\",\n"
        "      \"type\": \"string\",\n"
        "      \"mentions\": [\n"
        "        { \"doc_id\": \"string\", \"text\": \"string\" }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        "  \"relations\": [\n"
        "    {\n"
        "      \"source\": \"entity_id\",\n"
        "      \"target\": \"entity_id\",\n"
        "      \"relation\": \"string\",\n"
        "      \"evidence_doc_id\": \"string\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Here is the input JSON you should analyze:\n\n" + json.dumps(llm_input, ensure_ascii=False)
    )

    # 6) Call LLM and parse JSON
    llm_result = call_llm_for_json(
        system_prompt=system_prompt,
        user_content=user_content,
    )

    entities_raw = llm_result.get("entities") or []
    relations_raw = llm_result.get("relations") or []

    # 7) Adapt to relationships endpoint shape
    canonical_entities: List[str] = []
    related_via_entities: Dict[str, List[str]] = {}
    all_related_docs: Set[str] = set()

    for ent in entities_raw:
        # Prefer a human-readable label based on the first non-empty mention text.
        # Many models return opaque ids like "e1", "e2"; we don't want to show those
        # in the UI. Instead, we use the surface text (e.g. "OpenAI") as the
        # entity name where possible.
        mentions = ent.get("mentions") or []
        human_label: str = ""
        for m in mentions:
            txt = str(m.get("text") or "").strip()
            if txt:
                human_label = txt
                break

        # Fallback to the raw id if there was no mention text.
        if not human_label:
            human_label = str(ent.get("id") or "").strip()

        ent_key = human_label
        if not ent_key:
            continue

        if ent_key not in canonical_entities:
            canonical_entities.append(ent_key)

        doc_ids_for_entity: Set[str] = set()
        for m in mentions:
            m_doc = str(m.get("doc_id") or "").strip()
            if not m_doc or m_doc == doc_id:
                continue
            doc_ids_for_entity.add(m_doc)

        if not doc_ids_for_entity:
            continue

        related_via_entities[ent_key] = sorted(doc_ids_for_entity)
        all_related_docs.update(doc_ids_for_entity)

    return {
        "success": True,
        "doc_id": doc_id,
        "entities": canonical_entities,
        "entities_count": len(canonical_entities),
        "related_via_entities": related_via_entities,
        "related_documents": sorted(all_related_docs),
        "related_documents_count": len(all_related_docs),
        # Extra AI-specific details for future UI/debugging.
        "ai_entities": entities_raw,
        "ai_relations": relations_raw,
    }
