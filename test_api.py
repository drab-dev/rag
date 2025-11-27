"""
Test Script for Hybrid Vector + Graph AI Retrieval Engine
Tests all endpoints and validates functionality
"""
import requests
import json
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


def print_separator(title: str):
    """Print a visual separator"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(result: Dict[str, Any]):
    """Pretty print JSON result"""
    print(json.dumps(result, indent=2))


def test_health_check():
    """Test health check endpoint"""
    print_separator("TEST 1: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print_result(response.json())
    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")


def test_root_endpoint():
    """Test root endpoint"""
    print_separator("TEST 2: Root Endpoint")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print_result(response.json())
    assert response.status_code == 200, "Root endpoint failed"
    print("✓ Root endpoint passed")


def test_add_documents():
    """Test adding documents"""
    print_separator("TEST 3: Adding Sample Documents")
    
    documents = [
        {
            "doc_id": "doc1",
            "text": "Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models. Deep learning uses neural networks with multiple layers.",
            "metadata": {"category": "AI", "source": "textbook"}
        },
        {
            "doc_id": "doc2",
            "text": "Natural language processing enables computers to understand and process human language. It involves techniques like tokenization, parsing, and semantic analysis.",
            "metadata": {"category": "NLP", "source": "research"}
        },
        {
            "doc_id": "doc3",
            "text": "Neural networks are computational models inspired by biological neurons. They consist of layers of interconnected nodes that process information through weighted connections.",
            "metadata": {"category": "AI", "source": "lecture"}
        }
    ]
    
    for doc in documents:
        print(f"\nAdding {doc['doc_id']}...")
        response = requests.post(f"{BASE_URL}/add_document", json=doc)
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"  Entities extracted: {result.get('entities_extracted', 0)}")
        print(f"  Sample entities: {result.get('entities', [])[:5]}")
        assert response.status_code == 200, f"Failed to add {doc['doc_id']}"
        time.sleep(0.5)  # Small delay between requests
    
    print("\n✓ All documents added successfully")


def test_get_stats():
    """Test statistics endpoint"""
    print_separator("TEST 4: System Statistics")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Status Code: {response.status_code}")
    print_result(response.json())
    assert response.status_code == 200, "Stats endpoint failed"
    print("✓ Stats retrieved successfully")


def test_semantic_search():
    """Test semantic search"""
    print_separator("TEST 5: Semantic Search")
    
    query = "deep learning and neural networks"
    print(f"Query: '{query}'")
    
    response = requests.get(f"{BASE_URL}/search", params={"q": query, "top_k": 3})
    print(f"\nStatus Code: {response.status_code}")
    result = response.json()
    
    print(f"\nResults count: {result.get('results_count', 0)}")
    for i, res in enumerate(result.get('results', []), 1):
        print(f"\n  Result {i}:")
        print(f"    Doc ID: {res['doc_id']}")
        print(f"    Relevance Score: {res['relevance_score']:.4f}")
        print(f"    Snippet: {res['document'][:100]}...")
    
    assert response.status_code == 200, "Semantic search failed"
    assert result.get('results_count', 0) > 0, "No results found"
    print("\n✓ Semantic search passed")


def test_get_document():
    """Test document retrieval"""
    print_separator("TEST 6: Document Retrieval")
    
    doc_id = "doc1"
    print(f"Retrieving: {doc_id}")
    
    response = requests.get(f"{BASE_URL}/document/{doc_id}")
    print(f"\nStatus Code: {response.status_code}")
    result = response.json()
    
    print(f"\nDoc ID: {result.get('doc_id')}")
    print(f"Found: {result.get('found')}")
    print(f"Metadata: {result.get('metadata')}")
    
    assert response.status_code == 200, "Document retrieval failed"
    assert result.get('found') == True, "Document not found"
    print("\n✓ Document retrieval passed")


def test_graph_neighbors():
    """Test graph neighbors"""
    print_separator("TEST 7: Graph Neighbors")
    
    doc_id = "doc1"
    depth = 2
    print(f"Getting neighbors for: {doc_id} (depth={depth})")
    
    response = requests.get(f"{BASE_URL}/graph_neighbors", params={"doc_id": doc_id, "depth": depth})
    print(f"\nStatus Code: {response.status_code}")
    result = response.json()
    
    print(f"\nTotal neighbors: {result.get('total_neighbors', 0)}")
    print(f"Document neighbors: {result.get('document_neighbors_count', 0)}")
    print(f"Entity neighbors: {result.get('entity_neighbors_count', 0)}")
    
    if result.get('document_neighbors'):
        print(f"\nDocument neighbors: {[n['node_id'] for n in result['document_neighbors'][:5]]}")
    
    if result.get('entity_neighbors'):
        print(f"Sample entities: {[n['node_id'] for n in result['entity_neighbors'][:10]]}")
    
    assert response.status_code == 200, "Graph neighbors failed"
    print("\n✓ Graph neighbors passed")


def test_relationships():
    """Test document relationships"""
    print_separator("TEST 8: Document Relationships")
    
    doc_id = "doc1"
    print(f"Getting relationships for: {doc_id}")
    
    response = requests.get(f"{BASE_URL}/relationships/{doc_id}")
    print(f"\nStatus Code: {response.status_code}")
    result = response.json()
    
    print(f"\nEntities count: {result.get('entities_count', 0)}")
    print(f"Related documents count: {result.get('related_documents_count', 0)}")
    
    if result.get('entities'):
        print(f"Sample entities: {result['entities'][:10]}")
    
    if result.get('related_documents'):
        print(f"Related documents: {result['related_documents']}")
    
    assert response.status_code == 200, "Relationships retrieval failed"
    print("\n✓ Relationships retrieval passed")


def test_hybrid_search():
    """Test hybrid search"""
    print_separator("TEST 9: Hybrid Search")
    
    query = "artificial intelligence and machine learning"
    print(f"Query: '{query}'")
    
    response = requests.get(f"{BASE_URL}/hybrid", params={"q": query, "top_k": 3, "depth": 2})
    print(f"\nStatus Code: {response.status_code}")
    result = response.json()
    
    print(f"\nVector hits: {result.get('vector_hits_count', 0)}")
    print(f"Graph expansion: {result.get('graph_expansion_count', 0)}")
    print(f"Total hybrid results: {result.get('hybrid_results_count', 0)}")
    print(f"Entities found: {result.get('entities_count', 0)}")
    
    print("\n--- Vector Search Results ---")
    for i, res in enumerate(result.get('vector_hits', []), 1):
        print(f"\n  {i}. Doc ID: {res['doc_id']}")
        print(f"     Relevance: {res['relevance_score']:.4f}")
        print(f"     Graph neighbors: {res.get('graph_neighbors_count', 0)}")
    
    if result.get('graph_expansion_count', 0) > 0:
        print("\n--- Graph Expansion Results ---")
        for i, res in enumerate(result.get('graph_expansion', []), 1):
            print(f"\n  {i}. Doc ID: {res['doc_id']}")
            print(f"     Source: {res.get('source')}")
    
    if result.get('entities_count', 0) > 0:
        print("\n--- Top Entities ---")
        for i, entity in enumerate(result.get('entities', [])[:5], 1):
            print(f"  {i}. {entity['entity']} (connected to {entity['related_document_count']} docs)")
    
    assert response.status_code == 200, "Hybrid search failed"
    assert result.get('hybrid_results_count', 0) > 0, "No hybrid results"
    print("\n✓ Hybrid search passed")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  HYBRID VECTOR + GRAPH AI RETRIEVAL ENGINE - TEST SUITE")
    print("=" * 80)
    print("\nMake sure the server is running: uvicorn backend.main:app --reload")
    print("Testing against:", BASE_URL)
    
    try:
        # Basic tests
        test_health_check()
        test_root_endpoint()
        
        # Document ingestion
        test_add_documents()
        test_get_stats()
        
        # Search tests
        test_semantic_search()
        test_get_document()
        
        # Graph tests
        test_graph_neighbors()
        test_relationships()
        
        # Hybrid search
        test_hybrid_search()
        
        # Summary
        print_separator("TEST SUMMARY")
        print("✓ All tests passed successfully!")
        print("\nThe Hybrid Vector + Graph AI Retrieval Engine is working correctly.")
        print("=" * 80 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to the server.")
        print("  Make sure the server is running with: uvicorn backend.main:app --reload")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(run_all_tests())
