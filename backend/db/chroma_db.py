"""
ChromaDB Module
Handles vector database operations using ChromaDB
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import os


class ChromaDBManager:
    """Manager for ChromaDB operations"""
    
    def __init__(self, persist_directory: str = "./data/chroma_store"):
        """
        Initialize ChromaDB client with persistence
        
        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = persist_directory
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Document embeddings collection"}
        )
    
    def add_document_to_chroma(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a document to ChromaDB
        
        Args:
            doc_id: Unique document identifier
            text: Document text content
            embedding: Pre-computed embedding vector
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful
        """
        try:
            # Prepare metadata (may be empty or None)
            meta = metadata or {}

            # Build arguments, only including metadatas if non-empty
            kwargs = {
                "ids": [doc_id],
                "embeddings": [embedding],
                "documents": [text],
            }

            if meta:
                kwargs["metadatas"] = [meta]

            # Add to collection
            self.collection.add(**kwargs)

            return True
        except Exception as e:
            print(f"Error adding document to ChromaDB: {e}")
            return False
    
    def semantic_search(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Perform semantic search using query embedding
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            Dictionary containing search results
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Format results
            formatted_results = {
                "doc_ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else []
            }
            
            return formatted_results
        except Exception as e:
            print(f"Error performing semantic search: {e}")
            return {
                "doc_ids": [],
                "documents": [],
                "metadatas": [],
                "distances": []
            }
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document data or None if not found
        """
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas", "embeddings"]
            )
            
            # Chroma may return lists or numpy arrays here; avoid direct
            # truth-value checks on the arrays to prevent ambiguity errors.
            ids = results.get("ids")
            documents = results.get("documents")
            metadatas = results.get("metadatas")
            embeddings = results.get("embeddings")
            
            if ids is not None and len(ids) > 0:
                return {
                    "doc_id": ids[0],
                    "document": documents[0] if documents is not None and len(documents) > 0 else None,
                    "metadata": metadatas[0] if metadatas is not None and len(metadatas) > 0 else None,
                    "embedding": embeddings[0] if embeddings is not None and len(embeddings) > 0 else None,
                }
            
            return None
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the collection.

        Args:
            doc_id: Document identifier

        Returns:
            True if the delete call to ChromaDB completed without raising.
        """
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def list_document_ids(self) -> List[str]:
        """Return a list of all document IDs stored in the collection."""
        try:
            results = self.collection.get()
            ids = results.get("ids") or []

            # Chroma may return a flat list or a list-of-lists depending on version.
            if ids and isinstance(ids[0], list):
                # Flatten one level if needed
                flat_ids: List[str] = []
                for chunk in ids:
                    flat_ids.extend(chunk)
                return flat_ids

            return list(ids)
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def count_documents(self) -> int:
        """
        Get the total number of documents in the collection
        
        Returns:
            Document count
        """
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error counting documents: {e}")
            return 0


# Global instance
_chroma_db = None


def get_chroma_db() -> ChromaDBManager:
    """Get the singleton ChromaDB manager instance"""
    global _chroma_db
    if _chroma_db is None:
        _chroma_db = ChromaDBManager()
    return _chroma_db
