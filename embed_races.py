#!/usr/bin/env python3
"""
Import script to create embeddings from PostgreSQL data.

Usage:
    python embed_races.py [--reset] [--batch-size 100]
"""

import argparse
import logging
import sys
from datetime import datetime

from ai.embeddings import sync_embeddings_from_postgres, get_embeddings_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Import race data to vector database")
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset vector database before import"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reset without confirmation"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Trail AI - Race Embeddings Import")
    print("=" * 60)
    
    try:
        # Initialize embeddings client
        embeddings_client = get_embeddings_client()
        
        # Get current stats
        current_stats = embeddings_client.get_stats()
        print(f"Current vector database stats:")
        print(f"  Total races: {current_stats['total_races']}")
        print(f"  Countries: {current_stats['countries']}")
        print(f"  Race types: {current_stats['race_types']}")
        print(f"  Sources: {current_stats['sources']}")
        
        # Reset database if requested
        if args.reset:
            if not args.force:
                print(f"\n⚠️  WARNING: This will delete all {current_stats['total_races']} races from vector database!")
                confirm = input("Are you sure? [y/N]: ").strip().lower()
                if confirm not in ['y', 'yes']:
                    print("Cancelled.")
                    sys.exit(0)
            
            print("\nResetting vector database...")
            success = embeddings_client.reset_database()
            if not success:
                print("❌ Failed to reset database")
                sys.exit(1)
            print("✅ Database reset successfully")
        
        # Sync embeddings from PostgreSQL
        print(f"\nSyncing embeddings from PostgreSQL...")
        start_time = datetime.now()
        
        count = sync_embeddings_from_postgres()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n" + "=" * 60)
        print("Import completed!")
        print(f"  Races processed: {count}")
        print(f"  Duration: {duration}")
        print(f"  Rate: {count / duration.total_seconds():.1f} races/second")
        
        # Get final stats
        final_stats = embeddings_client.get_stats()
        print(f"\nFinal vector database stats:")
        print(f"  Total races: {final_stats['total_races']}")
        print(f"  Countries: {final_stats['countries']}")
        print(f"  Race types: {final_stats['race_types']}")
        print(f"  Sources: {final_stats['sources']}")
        
        if final_stats['sample_countries']:
            print(f"  Sample countries: {', '.join(final_stats['sample_countries'][:5])}")
        
        if final_stats['sample_race_types']:
            print(f"  Sample race types: {', '.join(final_stats['sample_race_types'][:5])}")
        
        print("=" * 60)
        print("✅ Embeddings import successful!")
        
        # Test search functionality
        print(f"\n🔍 Testing search functionality...")
        test_query = "trail race in Serbia"
        test_results = embeddings_client.search_races(test_query, n_results=3)
        
        if test_results:
            print(f"✅ Search test successful - found {len(test_results)} results for '{test_query}'")
            for i, result in enumerate(test_results[:2], 1):
                metadata = result.get('metadata', {})
                name = metadata.get('name', 'Unknown')
                location = metadata.get('location', 'Unknown location')
                score = result.get('similarity_score', 0)
                print(f"  {i}. {name} in {location} (score: {score:.3f})")
        else:
            print("⚠️  Search test failed - no results found")
        
    except KeyboardInterrupt:
        print("\n\nImport cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()