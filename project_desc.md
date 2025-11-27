PROJECT TITLE:
Hybrid Vector + Graph AI Retrieval Engine (ChromaDB + NetworkX + FastAPI)

PROJECT GOAL:
Build a backend system that stores documents, generates AI embeddings, builds a relationship graph, and performs hybrid retrieval using both semantic similarity (vector search) and relationship reasoning (graph traversal).

TECH STACK:
- Python
- FastAPI
- ChromaDB (vector database)
- NetworkX (graph database)
- SentenceTransformers (embedding model)
- spaCy OR simple keyword extraction (entity extraction)
- Persist graph using pickle (.pkl file)
- Persist Chroma using local directory

ARCHITECTURE OVERVIEW:
User uploads documents → system generates embedding → stores in Chroma → extracts entities → builds graph → performs semantic search + graph reasoning → returns hybrid results.

WHAT TO BUILD (FULL DETAILS):

1. **Folder Structure**
/backend
    /db
        chroma_db.py
        graph_db.py
    /services
        ingest_service.py
        search_service.py
        hybrid_service.py
    main.py
/data
    graph_store.pkl
    chroma_store/  (auto-created)
/models
    embedding_model.py

2. **CHROMADB SETUP** (chroma_db.py)
- Initialize Chroma client with persistence directory "./data/chroma_store"
- Create/get a collection named "documents"
- Functions needed:
    - add_document_to_chroma(doc_id, text, embedding, metadata)
    - semantic_search(query, top_k)
    - get_document(doc_id)

3. **EMBEDDING MODEL (embedding_model.py)**
- Load a SentenceTransformer model: "all-MiniLM-L6-v2"
- Function: generate_embedding(text) → returns embedding list

4. **GRAPH DB SETUP (graph_db.py)**
- Initialize NetworkX Graph()
- Functions needed:
    - load_graph() → load from graph_store.pkl if exists
    - save_graph() → save to same file
    - add_document_node(doc_id)
    - add_entity_node(entity)
    - add_edge_between(doc_id, entity)
    - get_neighbors(node, depth=1)
    - get_all_nodes()
- graph should persist across server restarts using pickle

5. **ENTITY EXTRACTOR**
Simplest version:
- extract_entities(text) → split keywords:
    - lower()
    - remove stopwords
    - pick nouns OR top keywords
(Optional: spaCy NER)

6. **DOCUMENT INGESTION PIPELINE (ingest_service.py)**
Function: ingest_document(doc_id, text, metadata)
Steps:
    a) generate embedding
    b) store text + embedding + metadata in Chroma
    c) extract entities from text
    d) add doc_id node to graph
    e) for each entity:
          add entity node
          add edge between doc_id and entity
    f) save graph
Return success + stored metadata.

7. **SEMANTIC SEARCH (search_service.py)**
Function: semantic_search(query, top_k)
Steps:
    - generate query embedding
    - query Chroma 
    - return doc_ids + documents + metadata + distances

8. **GRAPH SEARCH**
Function: graph_neighbors(doc_id, depth)
Steps:
    - BFS traversal (NetworkX)
    - return reachable nodes up to N hops

9. **HYBRID SEARCH (hybrid_service.py)**
Function: hybrid_search(query, top_k=5)
Steps:
    1) vector_results = semantic_search(query)
    2) collect top N doc_ids
    3) for each doc_id:
           get graph neighbors (depth=1 or 2)
    4) combine results into a unified list
    5) return:
        {
          "vector_hits": [...],
          "graph_expansion": [...],
          "hybrid_results": [...]
        }

10. **FASTAPI SETUP (main.py)**
Endpoints needed:

POST /add_document
Request body: { doc_id: str, text: str, metadata: dict }
→ Calls ingest_document()

GET /search
Query param: q
→ Returns semantic_search(q)

GET /graph_neighbors
Query param: doc_id, depth
→ Returns list of graph neighbors

GET /hybrid
Query param: q
→ Returns hybrid_search(q)

GET /document/{doc_id}
→ Returns stored document from Chroma

11. **TEST CASES**
- Add 3 documents
- Query semantic search
- Query graph neighbors
- Query hybrid search
- Verify hybrid returns vector + graph results

WHAT TO OUTPUT:
- Fully working Python backend
- All modules imported correctly
- Code runs using "uvicorn main:app --reload"
- Contains comments and clean structure
