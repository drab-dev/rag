# Hybrid Vector + Graph AI Retrieval Engine

A powerful backend system that combines **semantic vector search** (ChromaDB) with **graph-based relationship reasoning** (NetworkX) to provide intelligent document retrieval capabilities.

## 🚀 Features

- **Semantic Vector Search**: Uses sentence embeddings (all-MiniLM-L6-v2) to find semantically similar documents
- **Graph-Based Relationships**: Builds entity-document relationship graphs for connected information discovery
- **Hybrid Retrieval**: Combines both approaches for comprehensive search results
- **Persistent Storage**: ChromaDB for vectors, pickle for graph persistence
- **RESTful API**: FastAPI-based endpoints for easy integration
- **Entity Extraction**: Automatic keyword extraction from documents

## 📁 Project Structure

```
hybrid/
├── backend/
│   ├── db/
│   │   ├── chroma_db.py         # ChromaDB vector database operations
│   │   └── graph_db.py          # NetworkX graph database operations
│   ├── services/
│   │   ├── ingest_service.py    # Document ingestion pipeline
│   │   ├── search_service.py    # Semantic search operations
│   │   └── hybrid_service.py    # Hybrid search combining vector + graph
│   └── main.py                  # FastAPI application
├── models/
│   └── embedding_model.py       # SentenceTransformer wrapper
├── data/
│   ├── chroma_store/            # ChromaDB persistence (auto-created)
│   └── graph_store.pkl          # Graph persistence (auto-created)
├── requirements.txt             # Python dependencies
├── test_api.py                  # Test suite
└── README.md                    # This file
```

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone or navigate to the project directory**:
   ```powershell
   cd C:\Users\Dell\Downloads\hybrid
   ```

2. **Create a virtual environment** (recommended):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Download NLTK stopwords** (first run only):
   ```powershell
   python -c "import nltk; nltk.download('stopwords')"
   ```

## 🚀 Running the Application

### Start the Server

```powershell
uvicorn backend.main:app --reload
```

The server will start at `http://localhost:8000`

### Access API Documentation

FastAPI provides automatic interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### Document Management

#### Add Single Document
```http
POST /add_document
Content-Type: application/json

{
  "doc_id": "doc1",
  "text": "Your document text here...",
  "metadata": {
    "category": "AI",
    "source": "research"
  }
}
```

#### Add Multiple Documents
```http
POST /add_documents
Content-Type: application/json

{
  "documents": [
    {
      "doc_id": "doc1",
      "text": "Document 1 text...",
      "metadata": {}
    },
    {
      "doc_id": "doc2",
      "text": "Document 2 text...",
      "metadata": {}
    }
  ]
}
```

### Search Operations

#### Semantic Search
```http
GET /search?q=machine learning&top_k=5
```

Returns documents ranked by semantic similarity to the query.

#### Hybrid Search
```http
GET /hybrid?q=artificial intelligence&top_k=5&depth=2
```

Combines semantic search with graph traversal to find related documents.

#### Get Document
```http
GET /document/doc1
```

Retrieve a specific document by ID.

### Graph Operations

#### Get Graph Neighbors
```http
GET /graph_neighbors?doc_id=doc1&depth=1
```

Get all nodes connected to a document within specified depth.

#### Get Document Relationships
```http
GET /relationships/doc1
```

Get detailed relationship information including entities and related documents.

### System Information

#### System Statistics
```http
GET /stats
```

Returns statistics about documents, graph nodes, and system status.

#### Health Check
```http
GET /health
```

Check if the service is running.

## 🧪 Testing

Run the comprehensive test suite:

```powershell
python test_api.py
```

The test script will:
1. Check server health
2. Add sample documents
3. Test semantic search
4. Test graph operations
5. Test hybrid search
6. Validate all results

## 🔧 How It Works

### Document Ingestion Pipeline

1. **Generate Embedding**: Text is converted to a 384-dimensional vector using SentenceTransformer
2. **Store in ChromaDB**: Vector and text are persisted in the vector database
3. **Extract Entities**: Keywords are extracted using stopword filtering and frequency analysis
4. **Build Graph**: Document and entity nodes are created with edges connecting them
5. **Persist Graph**: Graph is saved to disk using pickle

### Hybrid Search Process

1. **Vector Search**: Query is embedded and used to find semantically similar documents
2. **Graph Expansion**: For each result, traverse the graph to find connected documents
3. **Combine Results**: Merge vector results with graph-discovered documents
4. **Return Unified Response**: Provide comprehensive results with both sources

## 📊 Example Use Cases

### 1. Research Paper Discovery
- Store research papers as documents
- Query for specific topics
- Discover related papers through shared entities (authors, keywords, concepts)

### 2. Knowledge Base Search
- Build a company knowledge base
- Semantic search finds relevant articles
- Graph traversal discovers related documentation

### 3. Content Recommendation
- Store content items (articles, videos, etc.)
- Find similar content through embeddings
- Recommend related content through graph connections

## 🎯 Configuration

### Embedding Model
The system uses `all-MiniLM-L6-v2` by default. To change:
- Edit `models/embedding_model.py`
- Replace model name in `SentenceTransformer()` initialization

### Storage Paths
Default storage locations:
- ChromaDB: `./data/chroma_store`
- Graph: `./data/graph_store.pkl`

To change, modify the initialization parameters in `backend/db/` modules.

### Entity Extraction
Configure in `backend/services/ingest_service.py`:
- `min_length`: Minimum keyword length (default: 3)
- `max_entities`: Maximum entities per document (default: 20)

## 📝 Example Usage

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Add a document
doc = {
    "doc_id": "ml_basics",
    "text": "Machine learning is a method of data analysis that automates analytical model building.",
    "metadata": {"topic": "ML"}
}
response = requests.post(f"{BASE_URL}/add_document", json=doc)
print(response.json())

# Search
response = requests.get(f"{BASE_URL}/search", params={"q": "data analysis", "top_k": 3})
results = response.json()
for result in results["results"]:
    print(f"Doc: {result['doc_id']}, Score: {result['relevance_score']}")

# Hybrid search
response = requests.get(f"{BASE_URL}/hybrid", params={"q": "machine learning", "top_k": 3})
hybrid_results = response.json()
print(f"Total results: {hybrid_results['hybrid_results_count']}")
```

## 🔍 Troubleshooting

### Import Errors
If you encounter import errors, make sure you're running commands from the project root directory:
```powershell
cd C:\Users\Dell\Downloads\hybrid
```

### NLTK Stopwords Error
Download stopwords:
```powershell
python -c "import nltk; nltk.download('stopwords')"
```

### ChromaDB Errors
If ChromaDB has issues, delete the data directory and restart:
```powershell
Remove-Item -Recurse -Force data
```

### Port Already in Use
If port 8000 is in use, specify a different port:
```powershell
uvicorn backend.main:app --reload --port 8001
```

## 🚧 Future Enhancements

- [ ] Add spaCy NER for better entity extraction
- [ ] Implement document update/delete operations
- [ ] Add authentication and rate limiting
- [ ] Support for document chunking for large texts
- [ ] GraphQL API endpoint
- [ ] Docker containerization
- [ ] Batch vector search optimization
- [ ] Graph visualization endpoint

## 📄 License

This project is open source and available under the MIT License.

## 👥 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## 📧 Support

For questions or issues, please open an issue on the project repository.

---

**Built with**: FastAPI, ChromaDB, NetworkX, SentenceTransformers, NLTK
