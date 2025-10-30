#!/usr/bin/env python3
"""
Direct JSONL to ChromaDB import - skipping PostgreSQL.

Usage:
    python embed_from_jsonl.py [--jsonl-file data/clean/races.jsonl]
"""

import argparse
import json
import logging
from pathlib import Path

# Import lightweight embeddings (no ChromaDB dependency)
try:
    from ai.embeddings import get_embeddings_client
except ImportError:
    from ai.lite import get_embeddings_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_races_from_jsonl(jsonl_path: str) -> list:
    """Load races from JSONL file."""
    races = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                race = json.loads(line)
                races.append(race)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed JSON on line {line_num}: {e}")
    
    logger.info(f"Loaded {len(races)} races from {jsonl_path}")
    return races


def main():
    parser = argparse.ArgumentParser(description="Import JSONL directly to vector database")
    parser.add_argument(
        "--jsonl-file", 
        default="data/clean/races.jsonl",
        help="Path to JSONL file"
    )
    parser.add_argument("--reset", action="store_true", help="Reset vector database first")
    
    args = parser.parse_args()
    
    if not Path(args.jsonl_file).exists():
        logger.error(f"JSONL file not found: {args.jsonl_file}")
        return 1
    
    # Initialize embeddings client
    embeddings_client = get_embeddings_client()
    
    # Reset if requested
    if args.reset:
        logger.info("Resetting vector database...")
        embeddings_client.reset_database()
    
    # Load and embed races
    races = load_races_from_jsonl(args.jsonl_file)
    
    if races:
        logger.info(f"Embedding {len(races)} races...")
        count = embeddings_client.add_races(races)
        logger.info(f"Successfully embedded {count} races")
        
        # Show stats
        stats = embeddings_client.get_stats()
        logger.info(f"Vector database now contains {stats['total_races']} races")
    
    return 0


if __name__ == "__main__":
    exit(main())