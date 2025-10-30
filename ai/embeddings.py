"""
Embeddings system for Trail AI using ChromaDB.

Handles:
- Creating and managing vector embeddings of race data
- Storing embeddings in ChromaDB
- Similarity search and retrieval
- Embedding updates and management
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Lightweight 80MB model
COLLECTION_NAME = "trail_races"


class TrailRaceEmbeddings:
    """Manages embeddings for trail race data."""
    
    def __init__(self, db_path: str = CHROMA_DB_PATH, model_name: str = EMBEDDING_MODEL):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Trail running race embeddings"}
        )
        
        logger.info(f"ChromaDB initialized at {self.db_path}")
        logger.info(f"Collection '{COLLECTION_NAME}' ready with {self.collection.count()} documents")
    
    def _race_to_text(self, race: Dict[str, Any]) -> str:
        """
        Convert race data to searchable text representation.
        
        Args:
            race: Race data dictionary
            
        Returns:
            Formatted text representation
        """
        parts = []
        
        # Basic info
        if race.get("name"):
            parts.append(f"Race: {race['name']}")
        
        if race.get("date"):
            parts.append(f"Date: {race['date']}")
        
        if race.get("location"):
            parts.append(f"Location: {race['location']}")
        
        if race.get("country"):
            parts.append(f"Country: {race['country']}")
        
        # Race details
        if race.get("distance_km"):
            parts.append(f"Distance: {race['distance_km']} km")
        
        if race.get("elevation_m"):
            parts.append(f"Elevation gain: {race['elevation_m']} m")
        
        if race.get("race_type"):
            parts.append(f"Type: {race['race_type']}")
        
        if race.get("terrain"):
            parts.append(f"Terrain: {race['terrain']}")
        
        # Organization info
        if race.get("organizer"):
            parts.append(f"Organizer: {race['organizer']}")
        
        if race.get("fee_eur"):
            parts.append(f"Fee: €{race['fee_eur']}")
        elif race.get("fee_rsd"):
            parts.append(f"Fee: {race['fee_rsd']} RSD")
        
        # Registration info
        if race.get("registration_opens"):
            parts.append(f"Registration opens: {race['registration_opens']}")
        
        if race.get("registration_closes"):
            parts.append(f"Registration closes: {race['registration_closes']}")
        
        return " | ".join(parts)
    
    def _create_race_metadata(self, race: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata dictionary for race.
        
        Args:
            race: Race data dictionary
            
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        # Include all non-null fields as metadata
        for key, value in race.items():
            if value is not None:
                # Convert dates and timestamps to strings
                if isinstance(value, datetime):
                    metadata[key] = value.isoformat()
                else:
                    metadata[key] = str(value)
        
        return metadata
    
    def add_races(self, races: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """
        Add race data to vector database.
        
        Args:
            races: List of race dictionaries
            batch_size: Number of races to process in each batch
            
        Returns:
            Number of races successfully added
        """
        if not races:
            return 0
        
        logger.info(f"Adding {len(races)} races to vector database...")
        
        added_count = 0
        for i in range(0, len(races), batch_size):
            batch = races[i:i + batch_size]
            
            # Prepare data for batch
            ids = []
            documents = []
            metadatas = []
            
            for race in batch:
                race_id = race.get("id")
                if not race_id:
                    logger.warning("Race missing ID, skipping")
                    continue
                
                # Convert race to searchable text
                text = self._race_to_text(race)
                metadata = self._create_race_metadata(race)
                
                ids.append(race_id)
                documents.append(text)
                metadatas.append(metadata)
            
            if ids:
                try:
                    # Add batch to ChromaDB
                    self.collection.add(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas
                    )
                    added_count += len(ids)
                    logger.info(f"Added batch {i//batch_size + 1}: {len(ids)} races")
                    
                except Exception as e:
                    logger.error(f"Failed to add batch {i//batch_size + 1}: {e}")
        
        logger.info(f"Successfully added {added_count} races to vector database")
        return added_count
    
    def search_races(self, query: str, n_results: int = 10, 
                    where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for races using semantic similarity.
        
        Args:
            query: Search query
            n_results: Number of results to return
            where: Optional metadata filters
            
        Returns:
            List of matching races with scores
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            races = []
            if results and results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    race = {
                        "document": doc,
                        "metadata": metadata,
                        "similarity_score": 1 - distance,  # Convert distance to similarity
                        "rank": i + 1
                    }
                    races.append(race)
            
            logger.info(f"Found {len(races)} races for query: '{query}'")
            return races
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_race_by_id(self, race_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific race by ID.
        
        Args:
            race_id: Race ID
            
        Returns:
            Race data or None if not found
        """
        try:
            results = self.collection.get(
                ids=[race_id],
                include=["documents", "metadatas"]
            )
            
            if results and results["documents"]:
                return {
                    "id": race_id,
                    "document": results["documents"][0],
                    "metadata": results["metadatas"][0] if results["metadatas"] else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get race {race_id}: {e}")
            return None
    
    def update_race(self, race_id: str, race_data: Dict[str, Any]) -> bool:
        """
        Update existing race in vector database.
        
        Args:
            race_id: Race ID
            race_data: Updated race data
            
        Returns:
            True if successful
        """
        try:
            text = self._race_to_text(race_data)
            metadata = self._create_race_metadata(race_data)
            
            self.collection.update(
                ids=[race_id],
                documents=[text],
                metadatas=[metadata]
            )
            
            logger.info(f"Updated race {race_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update race {race_id}: {e}")
            return False
    
    def delete_race(self, race_id: str) -> bool:
        """
        Delete race from vector database.
        
        Args:
            race_id: Race ID
            
        Returns:
            True if successful
        """
        try:
            self.collection.delete(ids=[race_id])
            logger.info(f"Deleted race {race_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete race {race_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.
        
        Returns:
            Statistics dictionary
        """
        count = self.collection.count()
        
        # Get sample of races to analyze
        sample = self.collection.peek(limit=100)
        
        countries = set()
        race_types = set()
        sources = set()
        
        if sample and sample["metadatas"]:
            for metadata in sample["metadatas"]:
                if metadata.get("country"):
                    countries.add(metadata["country"])
                if metadata.get("race_type"):
                    race_types.add(metadata["race_type"])
                if metadata.get("source"):
                    sources.add(metadata["source"])
        
        return {
            "total_races": count,
            "countries": len(countries),
            "race_types": len(race_types),
            "sources": len(sources),
            "sample_countries": list(countries)[:10],
            "sample_race_types": list(race_types)[:10],
            "sample_sources": list(sources)
        }
    
    def reset_database(self) -> bool:
        """
        Reset the vector database (delete all data).
        
        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Trail running race embeddings"}
            )
            logger.warning("Vector database reset - all data deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False


def get_embeddings_client() -> TrailRaceEmbeddings:
    """Get or create global embeddings client."""
    global _embeddings_client
    if '_embeddings_client' not in globals():
        _embeddings_client = TrailRaceEmbeddings()
    return _embeddings_client


def load_races_from_postgres() -> List[Dict[str, Any]]:
    """
    Load race data from PostgreSQL database.
    
    Returns:
        List of race dictionaries
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "traildb"),
            user=os.getenv("DB_USER", "trailuser"),
            password=os.getenv("DB_PASSWORD", "trailpass"),
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM races ORDER BY created_at DESC")
            races = [dict(row) for row in cur.fetchall()]
        
        conn.close()
        logger.info(f"Loaded {len(races)} races from PostgreSQL")
        return races
        
    except Exception as e:
        logger.error(f"Failed to load races from PostgreSQL: {e}")
        return []


def sync_embeddings_from_postgres() -> int:
    """
    Sync embeddings from PostgreSQL database.
    
    Returns:
        Number of races processed
    """
    races = load_races_from_postgres()
    if not races:
        return 0
    
    embeddings_client = get_embeddings_client()
    return embeddings_client.add_races(races)