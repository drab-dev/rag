# Frontend UI – Vite + React

This document describes the completed frontend UI for the Hybrid Vector + Graph AI Retrieval Engine, how it connects to the existing FastAPI backend, and how to run it locally.

The frontend provides:
- Document upload with **doc_id** + **text**
- Semantic search
- Hybrid search (vector + graph + combined ranking)
- Result visualization (doc IDs, scores, text snippets)
- System statistics (documents, graph nodes, graph edges, document/entity node counts)
- Graph relationship viewer (entities, related documents, graph neighbors)
- Direct interaction with the already implemented and tested backend

The right side of the screen is dedicated to stats and graph information; all other panels are on the left, as requested.

---

## 1. Tech Stack & Directory Layout

- **Framework**: React 18 (functional components + hooks)
- **Bundler/Dev Server**: Vite 5 with `@vitejs/plugin-react-swc`
- **Language**: JavaScript (JSX)
- **Styling**: CSS (single app-wide stylesheet)

From the project root `hybrid/`:

- `frontend/`
  - `package.json` – Vite + React config and scripts
  - `vite.config.mjs` – Vite configuration (React plugin, dev server port)
  - `index.html` – HTML entry point for Vite
  - `src/`
    - `main.jsx` – React entry point (mounts `<App />`)
    - `App.jsx` – All panels and business logic
    - `styles.css` – Layout and visual styles

The backend remains in `backend/` and is not modified.

---

## 2. Backend Connection

All frontend calls go to the existing FastAPI backend.

The base URL is defined in `src/App.jsx`:

```js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

- By default, the frontend expects the backend at `http://localhost:8000`.
- To change this, create `frontend/.env` with, for example:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Restart `npm run dev` after changing env vars.

### 2.1 Endpoints Used

The frontend uses only your existing endpoints:

1. **POST /add_document**  – add a document
2. **GET /search**         – semantic search
3. **GET /hybrid**         – hybrid search
4. **GET /stats**          – system statistics
5. **GET /relationships/{doc_id}** – entity/document relationships
6. **GET /graph_neighbors** – neighbors for a document at a given depth

CORS is already enabled in the backend (`CORSMiddleware` with `allow_origins=['*']`), so the browser can call the backend directly from the Vite dev server.

---

## 3. UI Panels and Behavior

### 3.1 Left Side – Main Workspace

#### 3.1.1 Document Upload Panel (Section 1)

**Location**: Top-left card in `App.jsx`.

**Fields:**
- `doc_id` – text input
- `document text` – textarea
- Button – **"Add Document"**

**Functionality:**
- Validates that both `doc_id` and `text` are non-empty.
- Sends:

```http
POST /add_document
Content-Type: application/json

{
  "doc_id": "<value from input>",
  "text": "<value from textarea>",
  "metadata": {}
}
```

- On success:
  - Displays an inline success message with the number of entities extracted.
  - Clears `doc_id` and `text` fields.
- On error:
  - Displays an inline error message with the backend error message (HTTP 4xx/5xx) or a generic failure.

#### 3.1.2 Semantic Search Panel (Section 2)

**Location**: Card below the upload panel.

**Fields:**
- Search bar (single shared query input)
- Button: **"Semantic Search"**

**Functionality:**
- On click, if query is non-empty, calls:

```http
GET /search?q=<query>&top_k=10
```

- On success, stores and displays the results.
- On error, displays a small error line in red under the panel.

#### 3.1.3 Semantic Search Results (Section 2 display)

**Location**: Card below the search panel.

**Behavior:**
- Displays up to the **top 10** results (client-side slice) from `/search`.
- For each result, it shows:
  - **Doc ID** – `result.doc_id`
  - **Relevance score** – `result.relevance_score` formatted to 4 decimal places
  - **Text snippet** – first ~220 characters of `result.document`
  - **Metadata** – optional, rendered as JSON if present

If no semantic search has been run yet or returns 0 results, an empty-state message is shown.

#### 3.1.4 Hybrid Search Panel (Section 3 – same card as search)

**Fields:**
- Uses the same shared search input as semantic search
- Button: **"Hybrid Search"**

**Functionality:**
- On click, if query is non-empty, calls:

```http
GET /hybrid?q=<query>&top_k=5&depth=2
```

- On success, stores the entire hybrid response.
- On error, shows a red error message in the search card.

#### 3.1.5 Hybrid Search Results (Section 3 display)

**Location**: Card below semantic results.

The response is split into **three logical sections**:

1. **Vector Hits**
   - Uses `vector_hits` and `vector_hits_count`.
   - For each vector hit:
     - Shows Doc ID, relevance score, snippet.
     - Shows `graph_neighbors_count` from the augmented results.
     - Tags the result with a small `vector` pill.

2. **Graph Expansion Results**
   - Uses `graph_expansion` and `graph_expansion_count`.
   - For each result:
     - Shows Doc ID and snippet.
     - Tags with a `graph_expansion` pill.
   - Also shows **Top Entities** from `entities`:
     - `entity` name
     - `related_document_count`
     - `related_documents` list displayed inline.

3. **Combined Hybrid Results (Final Ranking)**
   - Uses `hybrid_results` and `hybrid_results_count`.
   - For each combined result:
     - Shows Doc ID
     - Shows snippet
     - Shows relevance score if available
     - Shows `source` (either `vector_search` or `graph_expansion`) as a pill.

If no hybrid results exist yet, an empty-state helper text is displayed.

---

### 3.2 Right Side – Stats & Graph

#### 3.2.1 System Statistics Panel (Section 4)

**Location**: Top-right card.

**API Call:**

```http
GET /stats
```

**Behavior:**
- On mount, the frontend fetches stats once, then **refreshes every 5 seconds** using `setInterval` in a `useEffect` hook.
- The panel displays these fields in small card-style boxes:
  - **Documents (Chroma)** – `chromadb.total_documents`
  - **Total Nodes** – `graph.total_nodes`
  - **Total Edges** – `graph.total_edges`
  - **Document Nodes** – `graph.document_nodes`
  - **Entity Nodes** – `graph.entity_nodes`
  - **Status** – `system.status`

If the request fails, an error message is shown under the grid.

#### 3.2.2 Graph Relationships Panel (Section 5)

**Location:** Card under the stats panel on the right.

**Fields:**
- Input: **doc_id**
- Dropdown: **depth** (options: 1 or 2)
- Button: **"Get Relationships"**

**API Calls:**

1. `GET /relationships/{doc_id}`
2. `GET /graph_neighbors?doc_id=<doc_id>&depth=<depth>`

These are invoked together when the button is clicked (if `doc_id` is not empty).

**Display:**

- **Entities connected to document**
  - From `relationships.entities` and `relationships.entities_count`.
  - For each entity, shows a badge and the list of related documents from `related_via_entities[entity]`.

- **Related documents (via entities)**
  - Lists document IDs from `relationships.related_documents`.
  - Uses `related_documents_count` for the count.

- **Graph neighbors summary**
  - From `graph_neighbors` response.
  - Shows: total neighbors, document neighbor count, entity neighbor count.
  - Lists all neighbor node IDs from `all_neighbors`.

This textual view satisfies “visualize relationships (optional)” without adding a full graph visualizer yet. A future enhancement can take the same data and render a force-directed or node-link diagram.

---

## 4. Styling and Layout

- Two-column layout:
  - **Left**: upload panel, search controls, semantic results, hybrid results.
  - **Right**: stats panel, graph relationships panel.
- Dark theme with radial gradient background.
- Cards with rounded corners, subtle borders, and drop shadows.
- Result items use small badges for scores and sources (vector vs graph vs hybrid).
- Statistics presented as small rectangular cards in a responsive grid.

All styles are in `frontend/src/styles.css` and can be adjusted freely.

---

## 5. Running the Frontend (Vite) and Backend Together

### 5.1 Start the Backend

From the project root (`hybrid/`):

```bash
python run_dev.py
```

or, equivalently:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Verify the backend is healthy:

```bash
curl http://localhost:8000/health
```

### 5.2 Install Frontend Dependencies

From the project root:

```bash
cd frontend
npm install
```

This installs React, ReactDOM, Vite, and the React SWC plugin.

### 5.3 Run Vite Dev Server

Still in the `frontend/` directory:

```bash
npm run dev
```

Vite will show a local URL, usually:

- `http://localhost:5173`

Open that URL in your browser. The frontend will start making calls to `http://localhost:8000` (or the value you configured in `VITE_API_BASE_URL`).

### 5.4 (Optional) Build for Production

To build a production bundle:

```bash
cd frontend
npm run build
```

This outputs static files to `frontend/dist/`, which you can serve with any static file server.

---

## 6. How to Extend

- **Change API base URL:** update `VITE_API_BASE_URL` in `frontend/.env`.
- **Add new backend endpoints:** add new `fetch` calls and UI elements in `src/App.jsx`.
- **Add graph visualization:** consume the data from `/relationships` and `/graph_neighbors` to render a graph using a visualization library in a dedicated component.
- **Refactor UI:** you can split `App.jsx` into smaller components (e.g., `UploadPanel`, `SearchPanel`, `StatsPanel`, `GraphPanel`) without changing any backend contracts.
