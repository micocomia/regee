# retrieval.py
import numpy as np
import random
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
                                       num_contexts: int = 3,
                                       exclude_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve high-quality contexts for question generation with improved diversity.
        
        Args:
            topic: Optional topic to generate questions about
            num_contexts: Number of contexts to retrieve
            exclude_ids: List of document IDs to exclude from retrieval
            
        Returns:
            List of relevant document chunks for question generation
        """
        # If no specific topic, sample from a variety of educational queries
        diverse_queries = [
            "key concepts and definitions",
            "important principles and methodology",
            "significant findings and results",
            "critical analysis and evaluation",
            "practical applications and examples",
            "theoretical framework and models",
            "challenges and limitations",
            "future directions and implications"
        ]
        
        # Create topic-specific queries if a topic is provided
        if topic:
            topic_queries = [
                f"key concepts about {topic}",
                f"important definitions related to {topic}",
                f"main principles of {topic}",
                f"complex aspects of {topic}",
                f"details about {topic}",
                f"{topic}"
            ]
            # Use topic queries + a few diverse queries
            queries = topic_queries + random.sample(diverse_queries, 2)
        else:
            # Randomly select diverse queries to avoid always using the same ones
            queries = random.sample(diverse_queries, min(5, len(diverse_queries)))
        
        all_results = []
        
        # Retrieve results for each query and combine
        for query in queries:
            results = self.retrieve(
                query=query,
                top_k=max(3, num_contexts // len(queries) + 1)  # Ensure at least 3 results per query
            )
            all_results.extend(results)
        
        # Remove duplicates and excluded IDs
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result["id"] not in seen_ids and (exclude_ids is None or result["id"] not in exclude_ids):
                seen_ids.add(result["id"])
                unique_results.append(result)
        
        # Enhance diversity by grouping contexts by their embedded topics
        topic_groups = {}
        for result in unique_results:
            # Extract potential topics from the content
            content = result["content"]
            potential_topics = []
            
            # Check metadata for topics
            if "metadata" in result and "topics" in result["metadata"]:
                metadata_topics = result["metadata"]["topics"]
                if isinstance(metadata_topics, list):
                    potential_topics.extend(metadata_topics)
                elif isinstance(metadata_topics, str):
                    potential_topics.extend([t.strip() for t in metadata_topics.split(',')])
            
            # If no topics in metadata, use a simple extraction
            if not potential_topics:
                # Identify capitalized terms as potential topics
                import re
                capitalized_terms = re.findall(r'\b[A-Z][a-z]{3,}\b', content)
                if capitalized_terms:
                    potential_topics = capitalized_terms[:3]  # Take up to 3 capitalized terms
            
            # Use the first topic as the group key, or "general" if none found
            group_key = potential_topics[0].lower() if potential_topics else "general"
            
            if group_key not in topic_groups:
                topic_groups[group_key] = []
            topic_groups[group_key].append(result)
        
        # Select a balanced set of results from each topic group
        balanced_results = []
        
        # First, determine how many results to take from each group
        num_groups = len(topic_groups)
        base_count = num_contexts // num_groups if num_groups > 0 else 0
        remainder = num_contexts % num_groups if num_groups > 0 else 0
        
        # Take at least one result from each group, distributing the remainder
        for group_key, group_results in topic_groups.items():
            group_count = base_count + (1 if remainder > 0 else 0)
            if remainder > 0:
                remainder -= 1
                
            # Sort group by quality score
            group_results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            balanced_results.extend(group_results[:group_count])
        
        # If we still need more results to reach num_contexts
        if len(balanced_results) < num_contexts:
            # Get all remaining results
            remaining = [r for r in unique_results if r not in balanced_results]
            remaining.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            balanced_results.extend(remaining[:num_contexts - len(balanced_results)])
        
        return balanced_results[:num_contexts]
        
    def get_available_topics(self) -> List[str]:
        """
        Get all available topics in the vector store.
        
        Returns:
            List of unique topics
        """
        return self.vector_store.get_topics()