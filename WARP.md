# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Key commands

### Backend (FastAPI + ChromaDB + NetworkX)

- Install Python dependencies (from repo root):
  ```bash
  pip install -r requirements.txt
  ```
- Download NLTK stopwords (first run only):
  ```bash
  python -c "import nltk; nltk.download('stopwords')"
  ```
- Start the backend in dev mode (auto-reload, cross-platform):
  ```bash
  python run_dev.py
  ```
  This runs `backend.main:app` on `http://127.0.0.1:8000` with reload on changes in `backend/` and `models/`.
- Alternative direct uvicorn invocation:
  ```bash
  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
  ```
- Production backend (Gunicorn + Uvicorn worker, expects `venv/` already set up):
  ```bash
  ./start_prod.sh
  ```
- Run the end‑to‑end API test script:
  ```bash
  python test_api.py
  ```
- Run a single test from `test_api.py` without editing the file (example – health check only):
  ```bash
  python -c "import test_api; test_api.test_health_check()"
  ```

### Frontend (Vite + React)

All commands run from `frontend/`:

- Install frontend deps:
  ```bash
  cd frontend
  npm install
  ```
- Run Vite dev server (default on `http://localhost:5173`):
  ```bash
  npm run dev
  ```
- Build production bundle to `frontend/dist/`:
  ```bash
  npm run build
  ```
- Preview built bundle with Vite’s preview server:
  ```bash
  npm run preview
  ```

The frontend reads its API base URL from `VITE_API_BASE_URL` (see `frontend/src/App.jsx`):

```bash
# example .env in frontend/
VITE_API_BASE_URL=http://localhost:8000
```

### Full stack local dev loop

1. From repo root, start backend:
   ```bash
   python run_dev.py
   ```
2. In another terminal, start frontend:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open the Vite URL (usually `http://localhost:5173`); the UI will call the FastAPI backend at `VITE_API_BASE_URL`.

### Nginx + production style deployment (summary)

For full details see `DEPLOYMENT.md`, but the high‑level flow is:

- Build frontend + set up Python env (from repo root):
  ```bash
  chmod +x deploy.sh
  ./deploy.sh
  ```
- Start backend (development‑style, no Gunicorn):
  ```bash
  source venv/bin/activate
  uvicorn backend.main:app --host 0.0.0.0 --port 8000
  ```
- For local Nginx testing on macOS:
  ```bash
  sudo nginx -c $(pwd)/nginx/nginx.local.conf
  ```
  This serves `frontend/dist` and proxies API routes to the backend on port 8000.
- For Linux/production, `DEPLOYMENT.md` documents copying `nginx/nginx.conf` into `/etc/nginx/nginx.conf` and running `./start_prod.sh` under a systemd service.

## Architecture overview

### High‑level layout

- `backend/` – FastAPI app and service layer.
- `models/` – Embedding and LLM client abstractions.
- `backend/db/` – ChromaDB vector store + NetworkX graph persistence.
- `backend/services/` – Business logic: ingestion, search, hybrid retrieval, relationships, deletion, entity extraction.
- `data/` – On‑disk persistence for ChromaDB and the NetworkX graph.
- `frontend/` – Vite + React SPA that drives all backend endpoints.
- `nginx/` – Example Nginx configs for local and production deployments.

### Backend: FastAPI application

- `backend/main.py` is the FastAPI entrypoint. It:
  - Configures CORS (wide open origins; suitable for local dev and the Vite frontend).
  - Wires HTTP endpoints to service functions in `backend/services/*` and DB facades in `backend/db/*`.
  - Exposes core routes:
    - Ingestion: `POST /add_document`, `POST /add_documents`.
    - Retrieval: `GET /search`, `GET /hybrid`, `GET /document/{doc_id}`, `GET /list_documents`.
    - Graph views: `GET /graph_neighbors`, `GET /relationships/{doc_id}`.
    - Ops/diagnostics: `GET /`, `GET /health`, `GET /stats`, `DELETE /document/{doc_id}`.
  - Implements a small in‑process cache for `/stats` so frequent polling (e.g. from the frontend dashboard) does not hammer ChromaDB/NetworkX.

- Request/response validation is done with Pydantic models defined inside `main.py` (e.g. `DocumentRequest`, `BatchDocumentRequest`).

### Backend: services layer

- Ingestion pipeline – `backend/services/ingest_service.py`:
  - Uses `models.embedding_model.generate_embedding()` (SentenceTransformers `all-MiniLM-L6-v2`) to produce a 384‑dim embedding.
  - Persists text + embedding (+ optional metadata) via `ChromaDBManager.add_document_to_chroma()`.
  - Extracts entities using spaCy‑backed `extract_entities_spacy` (see `backend/services/entity_extractor.py`).
  - Builds/updates the bipartite graph in `GraphDBManager` by adding the document node, entity nodes, and edges, then persists to `data/graph_store.pkl`.

- Semantic search – `backend/services/search_service.py`:
  - Generates a query embedding with the same model.
  - Calls `ChromaDBManager.semantic_search()` and post‑processes the raw Chroma result into a list of dicts with `relevance_score = 1 - distance` plus document text and metadata.
  - Also exposes helper routines such as `search_by_document_id` and `get_similar_documents` (used by the hybrid and AI relation services).

- Hybrid search – `backend/services/hybrid_service.py`:
  - Calls `semantic_search(...)` for initial vector hits.
  - Uses `GraphDBManager` to:
    - For each top vector hit, get its connected entities.
    - From those entities, collect related documents (excluding the source doc).
  - Constructs per‑doc vector and graph scores, normalizes both via `_normalize_scores`, and then computes a weighted hybrid score (`0.7 * vector + 0.3 * graph`).
  - Returns three coordinated views for the frontend:
    - `vector_hits`: ordered vector results annotated with graph scores.
    - `graph_expansion`: documents discovered purely via graph expansion.
    - `hybrid_results`: final merged ranking across all docs.

- Graph neighbors – `graph_neighbors(...)` (same module):
  - Runs a BFS over the NetworkX graph to collect neighbors up to a configurable depth.
  - Splits neighbors into `document_neighbors` and `entity_neighbors` based on node attributes.

- Relationships – `get_document_relationships(...)`:
  - First tries an AI‑powered path via `backend/services/ai_relation_service.analyze_document_relationships` when the Groq LLM client is configured.
  - Falls back to a pure graph‑based implementation that:
    - Finds entities connected to the document.
    - For each entity, finds related documents.
    - Returns `entities`, `related_via_entities`, and `related_documents` in a shape compatible with the frontend.

- Deletion – `backend/services/delete_service.py` (not detailed here but wired from `DELETE /document/{doc_id}`):
  - Orchestrates deleting both the Chroma document and its graph node (including orphaned entities) via `ChromaDBManager.delete_document` and `GraphDBManager.delete_document_node`.

### Backend: data access layer

- Vector store – `backend/db/chroma_db.py`:
  - `ChromaDBManager` wraps a persistent ChromaDB client backed by `./data/chroma_store`.
  - Key capabilities:
    - `add_document_to_chroma` – adds single documents with optional metadata.
    - `semantic_search` – thin wrapper over `collection.query`, returning flat lists of IDs, docs, metadatas, and distances.
    - `get_document` – fetches a single document, metadata, and embedding, handling Chroma’s different return shapes.
    - `delete_document`, `list_document_ids`, and `count_documents` for maintenance and diagnostics.
  - Exposed as a singleton via `get_chroma_db()`.

- Graph store – `backend/db/graph_db.py`:
  - `GraphDBManager` encapsulates a NetworkX graph persisted to `./data/graph_store.pkl`.
  - Models a bipartite graph:
    - Document nodes (`node_type='document'`).
    - Entity nodes (`node_type='entity'`).
  - Provides helpers for:
    - Adding nodes and edges (`add_document_node`, `add_entity_node`, `add_edge_between`).
    - Connectivity queries (`get_neighbors`, `get_document_entities`, `get_related_documents`).
    - Administration (`delete_document_node` with orphan entity cleanup, `node_exists`, `get_graph_stats`).
  - Also exposed as a singleton via `get_graph_db()`.

### Models and LLM integration

- Embeddings – `models/embedding_model.py`:
  - Lazily loads a single global `SentenceTransformer('all-MiniLM-L6-v2')` instance.
  - Provides `generate_embedding(text)` and `get_embedding_model()` helpers.

- Groq LLM client – `models/llm_client.py`:
  - Thin wrapper around the Groq Python SDK.
  - `is_llm_configured()` returns `True` only if the `groq` package is importable and `GROQ_API_KEY` is set.
  - `call_llm_for_json(...)` performs a chat completion and post‑processes the response to extract a strict JSON object.

- AI relation service – `backend/services/ai_relation_service.py`:
  - When enabled, powers the `/relationships/{doc_id}` endpoint with cross‑document entity linking and relation extraction.
  - Gathers graph neighbors and semantically similar docs, truncates content, and prompts the LLM for a structured `entities` + `relations` JSON payload.
  - Adapts the LLM output back into the same shape used by the legacy graph‑only implementation so the frontend does not need to branch.

### Frontend SPA

- Located in `frontend/` and implemented as a single‑page React app:
  - `src/main.jsx` boots the React tree.
  - `src/App.jsx` contains panels for:
    - Document upload (`/add_document`).
    - Semantic search (`/search`).
    - Hybrid search (`/hybrid`).
    - System stats (`/stats`) with periodic polling.
    - Graph relationships viewer (`/relationships/{doc_id}` + `/graph_neighbors`).
  - `src/styles.css` defines a two‑column layout (left: ingestion/search/results, right: stats/graph info) and the dark theme.
- All API calls are made against `API_BASE_URL`, which is derived from `VITE_API_BASE_URL` at build/dev time.

### Nginx and external access

- Example configs live under `nginx/`:
  - `nginx.local.conf` – for local testing (static frontend + reverse‑proxy to backend on port 8000, typically on `localhost:8080`).
  - `nginx.conf` – production‑style config intended for `/etc/nginx/nginx.conf` on Linux.
- `DEPLOYMENT.md` documents:
  - Mac local workflow using `brew install nginx` and `nginx.local.conf`.
  - Linux production workflow with systemd (`rag-backend.service`) and HTTPS via Lets Encrypt.

## Additional documentation

When you need more detail, prefer these project docs before inferring behavior:

- `README.md` – canonical high‑level overview, endpoint documentation, and example usages.
- `QUICKSTART.md` – minimal steps to bring up the backend and exercise the API.
- `DEPLOYMENT.md` – Nginx and production deployment details.
- `frontend_desc.md` – detailed description of the React UI, panel behavior, and how it maps to backend endpoints.
- `project_desc.md` – original architectural spec for the backend (useful to understand intended responsibilities).
- `WINDOWS_SETUP.md` – notes on Windows‑specific fixes and recommended ways to run the dev server.
