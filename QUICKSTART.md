# Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Download NLTK Data
```powershell
python -c "import nltk; nltk.download('stopwords')"
```

### 3. Start the Server
```powershell
uvicorn backend.main:app --reload
```

The server will be running at `http://localhost:8000`

## Test the API (2 minutes)

### Option 1: Run Automated Tests
```powershell
python test_api.py
```

### Option 2: Manual Testing

Open your browser and visit:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Option 3: Use curl/PowerShell

#### Add a Document
```powershell
curl -X POST "http://localhost:8000/add_document" `
  -H "Content-Type: application/json" `
  -d '{
    "doc_id": "test1",
    "text": "Artificial intelligence and machine learning are transforming technology",
    "metadata": {"category": "tech"}
  }'
```

#### Search
```powershell
curl "http://localhost:8000/search?q=machine%20learning&top_k=5"
```

#### Hybrid Search
```powershell
curl "http://localhost:8000/hybrid?q=artificial%20intelligence&top_k=3&depth=2"
```

## Quick Example with Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Add documents
docs = [
    {"doc_id": "d1", "text": "Python is a programming language", "metadata": {}},
    {"doc_id": "d2", "text": "Machine learning uses Python for AI", "metadata": {}},
    {"doc_id": "d3", "text": "Data science and Python are connected", "metadata": {}}
]

for doc in docs:
    requests.post(f"{BASE_URL}/add_document", json=doc)

# Search
result = requests.get(f"{BASE_URL}/search", params={"q": "Python programming"}).json()
print(f"Found {result['results_count']} results")

# Hybrid search
hybrid = requests.get(f"{BASE_URL}/hybrid", params={"q": "Python"}).json()
print(f"Hybrid results: {hybrid['hybrid_results_count']}")
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore the interactive API docs at http://localhost:8000/docs
3. Check system stats at http://localhost:8000/stats
4. Add your own documents and experiment!

## Common Commands

```powershell
# Start server
uvicorn backend.main:app --reload

# Run tests
python test_api.py

# Check server is running
curl http://localhost:8000/health

# View all endpoints
curl http://localhost:8000/

# Get statistics
curl http://localhost:8000/stats
```

## Troubleshooting

**Server won't start?**
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`

**Import errors?**
- Make sure you're in the project directory
- Activate virtual environment if using one

**NLTK errors?**
- Run: `python -c "import nltk; nltk.download('stopwords')"`

**Port 8000 in use?**
- Use different port: `uvicorn backend.main:app --reload --port 8001`

## What's Happening Under the Hood?

1. **Document Ingestion**: Text → Embedding (384-dim vector) → ChromaDB + Entity extraction → Graph
2. **Semantic Search**: Query → Embedding → Find similar vectors in ChromaDB
3. **Graph Search**: Start from document → Traverse relationships → Find connected documents
4. **Hybrid**: Combine both approaches for comprehensive results

## File Locations

- **ChromaDB data**: `./data/chroma_store/`
- **Graph data**: `./data/graph_store.pkl`
- **Logs**: Console output

To reset data, delete the `data` directory and restart the server.
