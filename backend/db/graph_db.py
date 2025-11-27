"""
Graph Database Module
Handles graph operations using NetworkX with pickle persistence
"""
import networkx as nx
import pickle
import os
from typing import List, Set, Dict, Any
from collections import deque


class GraphDBManager:
    """Manager for NetworkX graph operations"""
    
    def __init__(self, persist_path: str = "./data/graph_store.pkl"):
        """
        Initialize graph database
        
        Args:
            persist_path: Path to pickle file for persistence
        """
        self.persist_path = persist_path
        self.graph = self.load_graph()
    
    def load_graph(self) -> nx.Graph:
        """
        Load graph from pickle file if exists, otherwise create new graph
        
        Returns:
            NetworkX Graph instance
        """
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'rb') as f:
                    graph = pickle.load(f)
                print(f"Graph loaded from {self.persist_path}")
                return graph
            except Exception as e:
                print(f"Error loading graph: {e}. Creating new graph.")
                return nx.Graph()
        else:
            print("No existing graph found. Creating new graph.")
            return nx.Graph()
    
    def save_graph(self) -> bool:
        """
        Save graph to pickle file
        
        Returns:
            True if successful
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            
            with open(self.persist_path, 'wb') as f:
                pickle.dump(self.graph, f)
            
            return True
        except Exception as e:
            print(f"Error saving graph: {e}")
            return False
    
    def add_document_node(self, doc_id: str, **attributes) -> bool:
        """
        Add a document node to the graph
        
        Args:
            doc_id: Document identifier
            **attributes: Additional node attributes
            
        Returns:
            True if successful
        """
        try:
            self.graph.add_node(doc_id, node_type='document', **attributes)
            return True
        except Exception as e:
            print(f"Error adding document node: {e}")
            return False
    
    def add_entity_node(self, entity: str, **attributes) -> bool:
        """
        Add an entity node to the graph
        
        Args:
            entity: Entity identifier
            **attributes: Additional node attributes
            
        Returns:
            True if successful
        """
        try:
            self.graph.add_node(entity, node_type='entity', **attributes)
            return True
        except Exception as e:
            print(f"Error adding entity node: {e}")
            return False
    
    def add_edge_between(self, node1: str, node2: str, **attributes) -> bool:
        """
        Add an edge between two nodes
        
        Args:
            node1: First node identifier
            node2: Second node identifier
            **attributes: Additional edge attributes
            
        Returns:
            True if successful
        """
        try:
            self.graph.add_edge(node1, node2, **attributes)
            return True
        except Exception as e:
            print(f"Error adding edge: {e}")
            return False
    
    def get_neighbors(self, node: str, depth: int = 1) -> List[str]:
        """
        Get neighbors of a node up to specified depth using BFS
        
        Args:
            node: Node identifier
            depth: Maximum traversal depth
            
        Returns:
            List of neighbor node identifiers
        """
        if node not in self.graph:
            return []
        
        visited = set()
        queue = deque([(node, 0)])
        neighbors = []
        
        while queue:
            current_node, current_depth = queue.popleft()
            
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            # Don't include the starting node itself
            if current_node != node:
                neighbors.append(current_node)
            
            # Continue BFS if we haven't reached max depth
            if current_depth < depth:
                for neighbor in self.graph.neighbors(current_node):
                    if neighbor not in visited:
                        queue.append((neighbor, current_depth + 1))
        
        return neighbors
    
    def get_all_nodes(self) -> List[str]:
        """
        Get all nodes in the graph
        
        Returns:
            List of all node identifiers
        """
        return list(self.graph.nodes())
    
    def get_node_attributes(self, node: str) -> Dict[str, Any]:
        """
        Get attributes of a specific node
        
        Args:
            node: Node identifier
            
        Returns:
            Dictionary of node attributes
        """
        if node in self.graph:
            return dict(self.graph.nodes[node])
        return {}
    
    def get_document_entities(self, doc_id: str) -> List[str]:
        """
        Get all entities connected to a document
        
        Args:
            doc_id: Document identifier
            
        Returns:
            List of entity identifiers
        """
        if doc_id not in self.graph:
            return []
        
        entities = []
        for neighbor in self.graph.neighbors(doc_id):
            node_attrs = self.graph.nodes[neighbor]
            if node_attrs.get('node_type') == 'entity':
                entities.append(neighbor)
        
        return entities
    
    def get_related_documents(self, entity: str) -> List[str]:
        """
        Get all documents connected to an entity
        
        Args:
            entity: Entity identifier
            
        Returns:
            List of document identifiers
        """
        if entity not in self.graph:
            return []
        
        documents = []
        for neighbor in self.graph.neighbors(entity):
            node_attrs = self.graph.nodes[neighbor]
            if node_attrs.get('node_type') == 'document':
                documents.append(neighbor)
        
        return documents

    def delete_document_node(self, doc_id: str) -> bool:
        """Delete a document node and its incident edges from the graph.

        Also removes any orphaned entity nodes that end up with no remaining
        connections after the document is removed.
        """
        try:
            if doc_id not in self.graph:
                return False

            # Track neighboring entity nodes so we can clean up orphans
            neighbors = list(self.graph.neighbors(doc_id))

            # Remove the document node (edges are removed implicitly)
            self.graph.remove_node(doc_id)

            # Remove orphaned entities (no remaining degree)
            for neighbor in neighbors:
                attrs = self.graph.nodes.get(neighbor, {})
                if attrs.get("node_type") == "entity" and self.graph.degree(neighbor) == 0:
                    self.graph.remove_node(neighbor)

            return True
        except Exception as e:
            print(f"Error deleting document node from graph: {e}")
            return False
    
    def node_exists(self, node: str) -> bool:
        """
        Check if a node exists in the graph
        
        Args:
            node: Node identifier
            
        Returns:
            True if node exists
        """
        return node in self.graph
    
    def get_graph_stats(self) -> Dict[str, int]:
        """
        Get statistics about the graph
        
        Returns:
            Dictionary with graph statistics
        """
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "document_nodes": sum(1 for _, attrs in self.graph.nodes(data=True) 
                                 if attrs.get('node_type') == 'document'),
            "entity_nodes": sum(1 for _, attrs in self.graph.nodes(data=True) 
                               if attrs.get('node_type') == 'entity')
        }


# Global instance
_graph_db = None


def get_graph_db() -> GraphDBManager:
    """Get the singleton graph database manager instance"""
    global _graph_db
    if _graph_db is None:
        _graph_db = GraphDBManager()
    return _graph_db
