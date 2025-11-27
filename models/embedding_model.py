"""
Embedding Model Module
Provides a singleton wrapper for SentenceTransformer model
"""
from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingModel:
    """Singleton wrapper for SentenceTransformer model"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingModel, cls).__new__(cls)
            # Load the model once
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._instance
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for the given text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# Global instance
_embedding_model = None


def get_embedding_model() -> EmbeddingModel:
    """Get the singleton embedding model instance"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


def generate_embedding(text: str) -> List[float]:
    """
    Convenience function to generate embedding
    
    Args:
        text: Input text to embed
        
    Returns:
        Embedding vector as list of floats
    """
    model = get_embedding_model()
    return model.generate_embedding(text)
