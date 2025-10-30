"""
Lightweight embeddings alternative using TF-IDF.

For development/testing when you don't want heavy ML dependencies.
"""

import os
import json
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import numpy as np


class LightweightEmbeddings:
    """Lightweight TF-IDF based embeddings."""
    
    def __init__(self, db_path: str = "./data/tfidf"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        self.documents = []
        self.metadata = []
        self.vectors = None
        self.is_fitted = False
        
        # Try to load existing data
        self._load_data()
    
    def _save_data(self):
        """Save vectorizer and data."""
        with open(f"{self.db_path}/vectorizer.pkl", "wb") as f:
            pickle.dump(self.vectorizer, f)
        
        with open(f"{self.db_path}/documents.json", "w") as f:
            json.dump(self.documents, f)
        
        with open(f"{self.db_path}/metadata.json", "w") as f:
            json.dump(self.metadata, f)
        
        if self.vectors is not None:
            np.save(f"{self.db_path}/vectors.npy", self.vectors)
    
    def _load_data(self):
        """Load existing data if available."""
        try:
            with open(f"{self.db_path}/vectorizer.pkl", "rb") as f:
                self.vectorizer = pickle.load(f)
            
            with open(f"{self.db_path}/documents.json", "r") as f:
                self.documents = json.load(f)
            
            with open(f"{self.db_path}/metadata.json", "r") as f:
                self.metadata = json.load(f)
            
            if os.path.exists(f"{self.db_path}/vectors.npy"):
                self.vectors = np.load(f"{self.db_path}/vectors.npy")
                self.is_fitted = True
                
        except (FileNotFoundError, EOFError):
            pass
    
    def add_races(self, races: List[Dict[str, Any]]) -> int:
        """Add races and create TF-IDF vectors."""
        new_docs = []
        new_metadata = []
        
        for race in races:
            # Create text representation
            text_parts = []
            
            if race.get("name"):
                text_parts.append(race["name"])
            if race.get("location"):
                text_parts.append(race["location"])
            if race.get("country"):
                text_parts.append(race["country"])
            if race.get("race_type"):  
                text_parts.append(race["race_type"])
            if race.get("organizer"):
                text_parts.append(race["organizer"])
            
            text = " ".join(text_parts)
            new_docs.append(text)
            new_metadata.append(race)
        
        self.documents.extend(new_docs)
        self.metadata.extend(new_metadata)
        
        # Fit TF-IDF vectorizer
        self.vectors = self.vectorizer.fit_transform(self.documents)
        self.is_fitted = True
        
        # Save data
        self._save_data()
        
        return len(new_docs)
    
    def search_races(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Search using TF-IDF similarity."""
        if not self.is_fitted or len(self.documents) == 0:
            return []
        
        # Transform query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.vectors).flatten()
        
        # Get top results
        top_indices = np.argsort(similarities)[::-1][:n_results]
        
        results = []
        for i, idx in enumerate(top_indices):
            if similarities[idx] > 0:  # Only return matches with similarity > 0
                results.append({
                    "document": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "similarity_score": float(similarities[idx]),
                    "rank": i + 1
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "total_races": len(self.documents),
            "is_fitted": self.is_fitted,
            "vectorizer_features": len(self.vectorizer.vocabulary_) if self.is_fitted else 0
        }
    
    def reset_database(self) -> bool:
        """Reset all data."""
        self.documents = []
        self.metadata = []
        self.vectors = None
        self.is_fitted = False
        
        # Remove files
        for filename in ["vectorizer.pkl", "documents.json", "metadata.json", "vectors.npy"]:
            filepath = f"{self.db_path}/{filename}"
            if os.path.exists(filepath):
                os.remove(filepath)
        
        return True