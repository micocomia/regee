# retrieval.py
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from vector_store import VectorStore

class RetrievalSystem:
    """
    Retrieval system for finding relevant document chunks based on queries using ChromaDB.
    """
    def __init__(self, vector_store: VectorStore, 
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the retrieval system.
        
        Args:
            vector_store: VectorStore instance for document retrieval
            embedding_model: Name of the sentence-transformers model to use
        """
        self.vector_store = vector_store
        self.embedding_model = SentenceTransformer(embedding_model)
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Convert text to embedding vector.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        return self.embedding_model.encode(text, show_progress_bar=False)
    
    def retrieve(self, query: str, top_k: int = 5, 
                 filter_topics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks based on a query.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filter_topics: Optional list of topics to filter results
            
        Returns:
            List of relevant document chunks with metadata and scores
        """
        # Get the embedding for the query
        query_embedding = self.get_embedding(query)
        
        # Search the vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            k=top_k
            #filter_topics=filter_topics
        )
        
        # Compute additional relevance metrics
        return self.compute_relevance_scores(results)
    
    def compute_relevance_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compute additional relevance metrics for retrieved results.
        
        Args:
            results: List of retrieved documents
            
        Returns:
            Documents with additional relevance metrics
        """
        if not results:
            return []
            
        # ChromaDB already provides a similarity score, but we can add more metrics
        
        # For example, we could add recency boost if documents have timestamps
        for doc in results:
            # Check if there's a created_at field in metadata
            if "created_at" in doc["metadata"]:
                try:
                    # This is a simple example - you would use actual date parsing in production
                    # Add a small boost for newer documents (0.0 to 0.1)
                    recency_boost = 0.05  # Small constant boost for simplicity
                    doc["adjusted_score"] = doc["similarity"] + recency_boost
                except Exception:
                    doc["adjusted_score"] = doc["similarity"]
            else:
                doc["adjusted_score"] = doc["similarity"]
                
        # Re-sort results by adjusted score
        results.sort(key=lambda x: x["adjusted_score"], reverse=True)
            
        return results
    
    def retrieve_for_question_generation(self, topic: Optional[str] = None, 
                                       num_contexts: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve high-quality contexts for question generation.
        
        Args:
            topic: Optional topic to generate questions about
            num_contexts: Number of contexts to retrieve
            
        Returns:
            List of relevant document chunks for question generation
        """
        # Create queries focused on educational content
        if topic:
            # Create multiple queries to diversify results
            queries = [
                f"key concepts about {topic}",
                f"important definitions related to {topic}",
                f"main principles of {topic}",
                f"complex aspects of {topic}",
                f"details about {topic}",
                f"{topic}"
            ]
        else:
            # When no topic specified, look for educational content
            queries = [
                "important concepts and definitions",
                "key principles and methodologies",
                "significant findings and results",
                "critical analysis and evaluation"
            ]
        
        all_results = []
        
        # Retrieve results for each query and combine
        for query in queries:
            results = self.retrieve(
                query=query,
                top_k=num_contexts // len(queries) + 1  # Distribute contexts among queries
                #filter_topics=[topic] if topic else None
            )
            all_results.extend(results)
        
        # Remove duplicates (if any)
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                unique_results.append(result)
        
        # Filter out low-quality contexts for questions
        quality_results = []
        for result in unique_results:
            content = result["content"]
            
            # # Skip contexts that are too short or likely non-informative
            # if len(content.strip()) < 100:
            #     continue
                
            # Skip contexts that are just metadata or references
            # if content.count("\n") > content.count(". ") * 2:
            #     continue
                
            # # Skip contexts that likely contain image captions only
            # if content.count("[IMAGE") > 2 and len(content) < 300:
            #     continue
                
            # Contexts with bullets/numbers likely contain good educational content
            has_bullets = any(line.strip().startswith(("•", "-", "*", "1.", "2.")) for line in content.split("\n"))
            has_educational_markers = any(marker in content.lower() for marker in 
                                          ["definition", "concept", "principle", "method", 
                                           "example", "important", "note that", "key", "understand"])
            
            # Prioritize contexts with educational indicators
            if has_bullets or has_educational_markers:
                result["quality_score"] = 1.5 * result.get("adjusted_score", result.get("similarity", 0.5))
            else:
                result["quality_score"] = result.get("adjusted_score", result.get("similarity", 0.5))
                
            quality_results.append(result)
        
        # Sort by quality score and take top contexts
        quality_results.sort(key=lambda x: x["quality_score"], reverse=True)
        
        return quality_results[:num_contexts]
    
    def get_available_topics(self) -> List[str]:
        """
        Get all available topics in the vector store.
        
        Returns:
            List of unique topics
        """
        return self.vector_store.get_topics()