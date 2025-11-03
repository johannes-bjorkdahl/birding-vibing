#!/usr/bin/env python3
"""Daily database update script for DuckDB observations.

Fetches recent observations from Artportalen API and updates the database.
Designed to be run daily to keep the database current with recent observations.

Usage:
    python scripts/update_database.py [--days DAYS] [--db-path PATH] [--dry-run]
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DuckDBConnection, create_schema, validate_schema, IngestionPipeline
from src.api.artportalen_client import ArtportalenAPIClient
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_update.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def progress_callback(current: int, total: int, message: str):
    """Callback function for progress updates.
    
    Args:
        current: Current chunk number
        total: Total number of chunks
        message: Status message
    """
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"[{current}/{total} ({percentage:.1f}%)] {message}")


def main():
    """Main function for database updates."""
    parser = argparse.ArgumentParser(
        description="Update DuckDB database with recent observations from Artportalen API"
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to fetch (default: 30, to ensure coverage)'
    )
    
    parser.add_argument(
        '--db-path',
        type=Path,
        default=Config.DATABASE_PATH,
        help='Path to DuckDB database file'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for ingestion (default: 1000)'
    )
    
    parser.add_argument(
        '--rate-limit-delay',
        type=float,
        default=1.0,
        help='Delay between API requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - fetch but do not save to database'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip dates that already have data (default: True)'
    )
    
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Disable skipping existing data (force re-fetch)'
    )
    
    args = parser.parse_args()
    
    # Handle skip_existing flag
    skip_existing = args.skip_existing and not args.no_skip_existing
    
    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No data will be saved")
        logger.info("=" * 60)
    
    # Validate API key
    if not Config.ARTPORTALEN_API_KEY:
        logger.error("ARTPORTALEN_API_KEY not configured. Cannot fetch data.")
        return 1
    
    # Initialize database connection
    logger.info(f"Connecting to database: {args.db_path}")
    try:
        with DuckDBConnection(args.db_path) as db_conn:
            connection = db_conn.connection
            
            # Ensure schema exists
            if not validate_schema(connection):
                logger.info("Creating database schema...")
                if not create_schema(connection):
                    logger.error("Failed to create schema")
                    return 1
            
            # Initialize API client
            logger.info("Initializing Artportalen API client...")
            api_client = ArtportalenAPIClient(
                Config.ARTPORTALEN_API_BASE_URL,
                Config.ARTPORTALEN_API_KEY
            )
            
            if not api_client._is_authenticated():
                logger.error("Failed to authenticate with Artportalen API")
                return 1
            
            # Initialize ingestion pipeline
            pipeline = IngestionPipeline(
                connection,
                batch_size=args.batch_size,
                rate_limit_delay=args.rate_limit_delay
            )
            
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=args.days - 1)
            
            logger.info("=" * 60)
            logger.info("Database Update")
            logger.info("=" * 60)
            logger.info(f"Date range: {start_date} to {end_date} ({args.days} days)")
            logger.info(f"Skip existing: {skip_existing}")
            logger.info(f"Batch size: {args.batch_size}")
            logger.info(f"Rate limit delay: {args.rate_limit_delay}s")
            logger.info("=" * 60)
            
            # Define fetch function
            def fetch_data(start: date, end: date, limit: int = 1000, offset: int = 0):
                """Fetch data from API."""
                result = api_client.search_occurrences(
                    taxon_id=Config.ARTPORTALEN_BIRDS_TAXON_ID,
                    start_date=start,
                    end_date=end,
                    limit=limit,
                    offset=offset
                )
                return result
            
            # Process date range
            if args.dry_run:
                logger.info("DRY RUN: Would process date range, but skipping actual ingestion")
                # Still do a test fetch to verify API works
                logger.info("Testing API connection...")
                test_result = fetch_data(start_date, start_date, limit=10, offset=0)
                if 'error' in test_result:
                    logger.error(f"API test failed: {test_result['error']}")
                    return 1
                logger.info(f"✓ API test successful: {test_result.get('count', 0)} records available")
                logger.info("DRY RUN complete - no data was saved")
            else:
                logger.info("Starting data ingestion...")
                result = pipeline.process_date_range(
                    start_date=start_date,
                    end_date=end_date,
                    fetch_data_func=fetch_data,
                    skip_existing=skip_existing,
                    auto_split_large_chunks=True,
                    progress_callback=progress_callback
                )
                
                success = result.get("success", False)
                if success:
                    logger.info("=" * 60)
                    logger.info("✅ Database update completed successfully!")
                    logger.info("=" * 60)
                    
                    # Get statistics
                    stats = connection.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(DISTINCT observation_date) as unique_dates,
                            MIN(observation_date) as min_date,
                            MAX(observation_date) as max_date
                        FROM observations
                        WHERE observation_date >= ?
                    """, [start_date]).fetchone()
                    
                    logger.info(f"Records in updated range: {stats[0]:,}")
                    logger.info(f"Unique dates: {stats[1]}")
                    logger.info(f"Date range: {stats[2]} to {stats[3]}")
                else:
                    logger.error("Database update failed - check logs for details")
                    return 1
            
            return 0
            
    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

