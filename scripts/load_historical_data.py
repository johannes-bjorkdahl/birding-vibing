#!/usr/bin/env python3
"""Historical data loading script for DuckDB.

Loads historical bird observation data from Artportalen API into DuckDB database.
Supports date range processing, progress tracking, resume capability, and dry-run mode.
"""

import argparse
import logging
import sys
from datetime import datetime, date
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DuckDBConnection, create_schema, validate_schema, IngestionPipeline
from src.api.artportalen_client import ArtportalenAPIClient
from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_ingestion.log'),
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
    """Main function for historical data loading."""
    parser = argparse.ArgumentParser(
        description="Load historical bird observation data from Artportalen API into DuckDB"
    )
    
    parser.add_argument(
        "--start-year",
        type=int,
        default=2024,
        help="Start year for data loading (default: 2024)"
    )
    
    parser.add_argument(
        "--end-year",
        type=int,
        default=2024,
        help="End year for data loading (default: 2024)"
    )
    
    parser.add_argument(
        "--start-month",
        type=int,
        default=1,
        help="Start month (1-12, default: 1)"
    )
    
    parser.add_argument(
        "--end-month",
        type=int,
        default=12,
        help="End month (1-12, default: 12)"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/birds.duckdb",
        help="Path to DuckDB database file (default: data/birds.duckdb)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for ingestion (default: 1000)"
    )
    
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=0.5,
        help="Delay between API calls in seconds (default: 0.5)"
    )
    
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Do not skip existing data (reprocess all date ranges)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't actually load data, just test API calls"
    )
    
    parser.add_argument(
        "--taxon-id",
        type=int,
        default=Config.ARTPORTALEN_BIRDS_TAXON_ID,
        help=f"Artportalen taxon ID for birds (default: {Config.ARTPORTALEN_BIRDS_TAXON_ID})"
    )
    
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Maximum number of records to fetch per month (for testing, default: unlimited)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start_year > args.end_year:
        logger.error("Start year must be <= end year")
        sys.exit(1)
    
    if not (1 <= args.start_month <= 12) or not (1 <= args.end_month <= 12):
        logger.error("Months must be between 1 and 12")
        sys.exit(1)
    
    # Check API key
    if not Config.ARTPORTALEN_API_KEY:
        logger.error(
            "Artportalen API key not configured. "
            "Please set ARTPORTALEN_SLU_API_KEY in .streamlit/secrets.toml or as environment variable."
        )
        sys.exit(1)
    
    # Initialize database connection
    logger.info(f"Connecting to database: {args.db_path}")
    with DuckDBConnection(args.db_path) as db:
        # Create schema if needed
        if not validate_schema(db.connection):
            logger.info("Creating database schema...")
            if not create_schema(db.connection):
                logger.error("Failed to create schema")
                sys.exit(1)
        else:
            logger.info("Database schema validated")
        
        # Initialize API client
        api_client = ArtportalenAPIClient(
            base_url=Config.ARTPORTALEN_API_BASE_URL,
            api_key=Config.ARTPORTALEN_API_KEY
        )
        
        if not api_client._is_authenticated():
            logger.error("API client authentication failed")
            sys.exit(1)
        
        # Define date range
        start_date = datetime(args.start_year, args.start_month, 1)
        if args.end_month == 12:
            end_date = datetime(args.end_year + 1, 1, 1) - datetime.resolution
        else:
            end_date = datetime(args.end_year, args.end_month + 1, 1) - datetime.resolution
        
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No data will be loaded")
            # Test API call
            test_response = api_client.search_occurrences(
                taxon_id=args.taxon_id,
                start_date=start_date.date(),
                end_date=end_date.date(),
                limit=10
            )
            if "error" in test_response:
                logger.error(f"API test failed: {test_response['error']}")
                sys.exit(1)
            logger.info(f"API test successful - found {test_response.get('count', 0)} records")
            logger.info("Dry run complete - API is accessible")
            return
        
        # Initialize ingestion pipeline
        pipeline = IngestionPipeline(
            connection=db.connection,
            batch_size=args.batch_size,
            rate_limit_delay=args.rate_limit_delay
        )
        
        # Define fetch function with pagination support
        def fetch_data(start: date, end: date, offset: int = 0, limit: int = 1000):
            """Fetch data from API for date range with pagination."""
            return api_client.search_occurrences(
                taxon_id=args.taxon_id,
                start_date=start,
                end_date=end,
                limit=limit,
                offset=offset
            )
        
        # Process date range
        logger.info("Starting data ingestion...")
        if args.max_records:
            logger.info(f"TEST MODE: Limiting to {args.max_records} records per month")
        
        # Process date range with auto-splitting enabled by default
        result = pipeline.process_date_range(
            start_date=start_date,
            end_date=end_date,
            fetch_function=fetch_data,
            skip_existing=not args.no_skip_existing,
            progress_callback=progress_callback,
            max_records=args.max_records,
            auto_split_large_chunks=True  # Automatically split months >10,000 records
        )
        
        # Print summary
        logger.info("=" * 60)
        logger.info("Ingestion Summary:")
        logger.info(f"  Total chunks: {result['total_chunks']}")
        logger.info(f"  Processed chunks: {result['processed_chunks']}")
        logger.info(f"  Skipped chunks: {result['skipped_chunks']}")
        logger.info(f"  Total records ingested: {result['total_ingested']}")
        logger.info(f"  Total records failed: {result['total_failed']}")
        logger.info("=" * 60)
        
        if result['total_failed'] > 0:
            logger.warning(f"Some records failed to ingest. Check logs for details.")
            sys.exit(1)


if __name__ == "__main__":
    main()

