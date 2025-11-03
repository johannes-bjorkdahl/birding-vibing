"""Database management UI components for Streamlit app."""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import sys
from pathlib import Path
import threading
import time
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DuckDBConnection, validate_schema, IngestionPipeline
from src.api.artportalen_client import ArtportalenAPIClient
from src.config import Config

logger = logging.getLogger(__name__)


def get_database_stats(connection) -> Dict[str, Any]:
    """Get database statistics.
    
    Args:
        connection: DuckDB connection instance
        
    Returns:
        Dictionary with database statistics
    """
    try:
        stats = {}
        
        # Total records
        total_result = connection.execute("SELECT COUNT(*) FROM observations").fetchone()
        stats['total_records'] = total_result[0] if total_result else 0
        
        if stats['total_records'] == 0:
            return stats
        
        # Date range
        date_range = connection.execute("""
            SELECT MIN(observation_date), MAX(observation_date)
            FROM observations
        """).fetchone()
        stats['date_range'] = {
            'min': date_range[0],
            'max': date_range[1]
        }
        
        # API source distribution
        api_sources = connection.execute("""
            SELECT api_source, COUNT(*) as count
            FROM observations
            GROUP BY api_source
        """).fetchall()
        stats['api_sources'] = dict(api_sources)
        
        # Records per year
        records_per_year = connection.execute("""
            SELECT EXTRACT(YEAR FROM observation_date) as year, COUNT(*) as count
            FROM observations
            GROUP BY year
            ORDER BY year DESC
            LIMIT 10
        """).fetchall()
        stats['records_per_year'] = dict(records_per_year)
        
        # Unique species
        unique_species = connection.execute("""
            SELECT COUNT(DISTINCT species_name) FROM observations
        """).fetchone()
        stats['unique_species'] = unique_species[0] if unique_species else 0
        
        # Geographic coverage
        coord_stats = connection.execute("""
            SELECT 
                MIN(latitude) as min_lat,
                MAX(latitude) as max_lat,
                MIN(longitude) as min_lon,
                MAX(longitude) as max_lon
            FROM observations
        """).fetchone()
        
        stats['geographic'] = {
            'lat_range': (coord_stats[0], coord_stats[1]) if coord_stats[0] else None,
            'lon_range': (coord_stats[2], coord_stats[3]) if coord_stats[2] else None,
        }
        
        # Database file size
        db_path = Path(Config.DATABASE_PATH)
        if db_path.exists():
            stats['file_size_mb'] = db_path.stat().st_size / (1024 * 1024)
        else:
            stats['file_size_mb'] = 0
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {'error': str(e)}


def display_database_status():
    """Display database status and statistics."""
    api_info = st.session_state.unified_client.get_current_api_info()
    
    if not api_info.get("database_available", False):
        st.warning("⚠️ Database is not available. Check configuration and ensure database file exists.")
        return
    
    st.subheader("💾 Database Status")
    
    try:
        with DuckDBConnection(Config.DATABASE_PATH) as db_conn:
            connection = db_conn.connection
            
            # Validate schema
            if not validate_schema(connection):
                st.error("❌ Database schema is invalid. Please recreate the database.")
                return
            
            # Get statistics
            stats = get_database_stats(connection)
            
            if 'error' in stats:
                st.error(f"Failed to get database stats: {stats['error']}")
                return
            
            # Display statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", f"{stats.get('total_records', 0):,}")
            
            with col2:
                st.metric("Unique Species", f"{stats.get('unique_species', 0):,}")
            
            with col3:
                file_size = stats.get('file_size_mb', 0)
                st.metric("Database Size", f"{file_size:.2f} MB")
            
            with col4:
                if stats.get('date_range'):
                    date_range = stats['date_range']
                    if date_range['min'] and date_range['max']:
                        years = (date_range['max'] - date_range['min']).days / 365.25
                        st.metric("Date Range", f"{years:.1f} years")
            
            # Date range details
            if stats.get('date_range'):
                date_range = stats['date_range']
                if date_range['min'] and date_range['max']:
                    st.caption(f"📅 From {date_range['min']} to {date_range['max']}")
            
            # API source distribution
            if stats.get('api_sources'):
                st.subheader("Data Sources")
                api_sources = stats['api_sources']
                for source, count in api_sources.items():
                    st.caption(f"  • {source}: {count:,} records")
            
            # Records per year
            if stats.get('records_per_year'):
                st.subheader("Records by Year (Top 10)")
                year_df = pd.DataFrame([
                    {'Year': year, 'Records': count}
                    for year, count in stats['records_per_year'].items()
                ])
                st.dataframe(year_df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        logger.error(f"Database status error: {e}", exc_info=True)


def run_ingestion_job(
    start_date: date,
    end_date: date,
    progress_placeholder,
    status_placeholder
):
    """Run ingestion job in background thread.
    
    Args:
        start_date: Start date for ingestion
        end_date: End date for ingestion
        progress_placeholder: Streamlit placeholder for progress updates
        status_placeholder: Streamlit placeholder for status messages
    """
    try:
        status_placeholder.info("🔄 Starting ingestion...")
        
        # Initialize API client
        api_client = ArtportalenAPIClient(
            Config.ARTPORTALEN_API_BASE_URL,
            Config.ARTPORTALEN_API_KEY
        )
        
        if not api_client._is_authenticated():
            status_placeholder.error("❌ Failed to authenticate with Artportalen API")
            return
        
        # Initialize database connection
        with DuckDBConnection(Config.DATABASE_PATH) as db_conn:
            connection = db_conn.connection
            
            # Ensure schema exists
            from src.database.schema import create_schema
            if not validate_schema(connection):
                create_schema(connection)
            
            # Initialize pipeline
            pipeline = IngestionPipeline(
                connection,
                batch_size=1000,
                rate_limit_delay=1.0
            )
            
            # Define fetch function
            # Note: process_date_range calls fetch_function(start, end, offset, limit)
            def fetch_data(start: date, end: date, offset: int = 0, limit: int = 1000):
                result = api_client.search_occurrences(
                    taxon_id=Config.ARTPORTALEN_BIRDS_TAXON_ID,
                    start_date=start,
                    end_date=end,
                    limit=limit,
                    offset=offset
                )
                return result
            
            # Progress callback
            def progress_callback(current: int, total: int, message: str):
                progress = current / total if total > 0 else 0
                progress_placeholder.progress(progress)
                status_placeholder.info(f"📊 [{current}/{total}] {message}")
            
            # Convert dates to datetime
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.min.time())
            
            # Run ingestion
            result = pipeline.process_date_range(
                start_date=start_dt,
                end_date=end_dt,
                fetch_function=fetch_data,
                skip_existing=True,
                auto_split_large_chunks=True,
                progress_callback=progress_callback
            )
            
            # Final status
            if result.get('success', False):
                status_placeholder.success(
                    f"✅ Ingestion complete! "
                    f"Ingested {result.get('total_ingested', 0):,} records "
                    f"({result.get('processed_chunks', 0)} chunks processed)"
                )
            else:
                status_placeholder.warning(
                    f"⚠️ Ingestion completed with issues. "
                    f"Check logs for details. "
                    f"Ingested {result.get('total_ingested', 0):,} records."
                )
            
            progress_placeholder.progress(1.0)
            
    except Exception as e:
        status_placeholder.error(f"❌ Ingestion failed: {e}")
        logger.error(f"Ingestion error: {e}", exc_info=True)


def display_database_management():
    """Display database management interface."""
    st.header("💾 Database Management")
    
    api_info = st.session_state.unified_client.get_current_api_info()
    
    if not api_info.get("database_available", False):
        st.warning("⚠️ Database is not available. Please check configuration.")
        return
    
    if not Config.ARTPORTALEN_API_KEY:
        st.warning("⚠️ Artportalen API key is required for data ingestion.")
        return
    
    # Database Status Section
    with st.expander("📊 Database Statistics", expanded=True):
        display_database_status()
    
    st.divider()
    
    # Ingestion Section
    st.subheader("🔄 Data Ingestion")
    
    st.markdown("""
    Load historical data from Artportalen API into the local database.
    The ingestion process will automatically handle API limits and split large date ranges.
    """)
    
    # Skip existing option
    skip_existing = st.checkbox(
        "Skip existing data (recommended)",
        value=True,
        help="If checked, skip date ranges that already have data in the database. Uncheck to re-ingest existing data."
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_year = st.number_input(
            "Start Year",
            min_value=2005,
            max_value=date.today().year,
            value=2020,
            help="Start year for data ingestion"
        )
        start_month = st.number_input(
            "Start Month",
            min_value=1,
            max_value=12,
            value=1,
            help="Start month (1-12)"
        )
    
    with col2:
        end_year = st.number_input(
            "End Year",
            min_value=2005,
            max_value=date.today().year,
            value=date.today().year,
            help="End year for data ingestion"
        )
        end_month = st.number_input(
            "End Month",
            min_value=1,
            max_value=12,
            value=date.today().month,
            help="End month (1-12)"
        )
    
    # Calculate date range
    start_date = date(start_year, start_month, 1)
    if end_month == 12:
        end_date = date(end_year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(end_year, end_month + 1, 1) - timedelta(days=1)
    
    # Validate date range
    if start_date > end_date:
        st.error("❌ Start date must be before end date")
        return
    
    # Show date range info
    days = (end_date - start_date).days + 1
    months = days / 30.44
    st.info(f"📅 Date range: {start_date} to {end_date} ({days} days, ~{months:.1f} months)")
    
    # Warning for large ranges
    if days > 365:
        st.warning(
            f"⚠️ Large date range selected ({days} days). "
            f"This may take several hours to complete and make many API requests. "
            f"Consider starting with a smaller range for testing."
        )
    
    # Start ingestion button
    if 'ingestion_running' not in st.session_state:
        st.session_state.ingestion_running = False
    
    if st.button("🚀 Start Ingestion", type="primary", disabled=st.session_state.ingestion_running):
        st.session_state.ingestion_running = True
        st.session_state.ingestion_start_date = start_date
        st.session_state.ingestion_end_date = end_date
        st.session_state.ingestion_skip_existing = skip_existing  # Save checkbox state
        st.rerun()
    
    # Show ingestion progress if running
    if st.session_state.ingestion_running:
        # Create placeholders FIRST before any other operations
        progress_placeholder = st.progress(0)
        status_placeholder = st.empty()
        
        # Run ingestion synchronously
        start_date = st.session_state.ingestion_start_date
        end_date = st.session_state.ingestion_end_date
        skip_existing = st.session_state.get('ingestion_skip_existing', True)  # Get from session state
        
        # Show initial status immediately - this must happen before any blocking operations
        try:
            status_placeholder.info("🔄 Starting ingestion...")
            progress_placeholder.progress(0.05)  # Show initial progress
            
            # Log that we're starting
            logger.info(f"Starting ingestion: {start_date} to {end_date}, skip_existing={skip_existing}")
            
        except Exception as e:
            logger.error(f"Error showing initial status: {e}", exc_info=True)
        
        # Note: Streamlit doesn't support true background threads well
        # We'll run it synchronously but with progress updates
        try:
            
            # Initialize API client
            api_client = ArtportalenAPIClient(
                Config.ARTPORTALEN_API_BASE_URL,
                Config.ARTPORTALEN_API_KEY
            )
            
            if not api_client._is_authenticated():
                status_placeholder.error("❌ Failed to authenticate with Artportalen API")
                st.session_state.ingestion_running = False
                return
            
            # Initialize database connection
            with DuckDBConnection(Config.DATABASE_PATH) as db_conn:
                connection = db_conn.connection
                
                # Ensure schema exists
                from src.database.schema import create_schema
                if not validate_schema(connection):
                    create_schema(connection)
                
                # Initialize pipeline with optimized rate limiting
                # Reduced delay since we have retry logic for 429 errors
                pipeline = IngestionPipeline(
                    connection,
                    batch_size=1000,
                    rate_limit_delay=0.5  # Reduced from 2.0s - retry logic handles rate limits
                )
                
                # Define fetch function
                # Note: process_date_range calls fetch_function(start, end, offset, limit)
                def fetch_data(start: date, end: date, offset: int = 0, limit: int = 1000):
                    result = api_client.search_occurrences(
                        taxon_id=Config.ARTPORTALEN_BIRDS_TAXON_ID,
                        start_date=start,
                        end_date=end,
                        limit=limit,
                        offset=offset
                    )
                    return result
                
                # Progress callback
                def progress_callback(current: int, total: int, message: str):
                    progress = current / total if total > 0 else 0
                    progress_placeholder.progress(progress)
                    status_placeholder.info(f"📊 [{current}/{total}] {message}")
                
                # Convert dates to datetime
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.min.time())
                
                # Run ingestion
                result = pipeline.process_date_range(
                    start_date=start_dt,
                    end_date=end_dt,
                    fetch_function=fetch_data,
                    skip_existing=skip_existing,
                    auto_split_large_chunks=True,
                    progress_callback=progress_callback
                )
                
                # Final status
                total_ingested = result.get('total_ingested', 0)
                processed_chunks = result.get('processed_chunks', 0)
                skipped_chunks = result.get('skipped_chunks', 0)
                total_chunks = result.get('total_chunks', 0)
                
                if skipped_chunks == total_chunks and total_ingested == 0:
                    # All chunks were skipped
                    status_placeholder.warning(
                        f"⏭️ **All chunks skipped** - Data already exists for this date range!\n\n"
                        f"**Summary:**\n"
                        f"- Total chunks: {total_chunks}\n"
                        f"- Skipped (already exists): {skipped_chunks}\n"
                        f"- Records ingested: {total_ingested:,}\n\n"
                        f"**To re-ingest:** Uncheck 'Skip existing data' or select a different date range."
                    )
                elif result.get('success', False):
                    status_placeholder.success(
                        f"✅ **Ingestion complete!**\n\n"
                        f"**Summary:**\n"
                        f"- Records ingested: {total_ingested:,}\n"
                        f"- Chunks processed: {processed_chunks}/{total_chunks}\n"
                        f"- Chunks skipped: {skipped_chunks}\n"
                        f"- Records failed: {result.get('total_failed', 0):,}"
                    )
                else:
                    status_placeholder.warning(
                        f"⚠️ **Ingestion completed with issues**\n\n"
                        f"**Summary:**\n"
                        f"- Records ingested: {total_ingested:,}\n"
                        f"- Chunks processed: {processed_chunks}/{total_chunks}\n"
                        f"- Chunks skipped: {skipped_chunks}\n"
                        f"- Records failed: {result.get('total_failed', 0):,}\n\n"
                        f"Check logs for details."
                    )
                
                progress_placeholder.progress(1.0)
                
                # DON'T auto-rerun immediately - let user see results
                # Reset running flag but keep status visible
                st.session_state.ingestion_running = False
                
                # Add a button to refresh stats instead of auto-refresh
                if st.button("🔄 Refresh Statistics & Close", key="refresh_after_ingestion"):
                    st.rerun()
                
        except Exception as e:
            progress_placeholder.progress(1.0)
            error_msg = str(e)
            logger.error(f"Ingestion error: {e}", exc_info=True)
            
            # Show detailed error
            if "Conflicting lock" in error_msg or "lock" in error_msg.lower():
                status_placeholder.error(
                    "⚠️ **Database Lock Error**\n\n"
                    "The database is locked by another process.\n\n"
                    "**Solution:**\n"
                    "1. Refresh the page\n"
                    "2. Stop and restart the Streamlit app\n"
                    "3. Run ingestion from command line:\n"
                    "   ```bash\n"
                    "   uv run python scripts/load_historical_data.py --start-year 2025 --start-month 10 --end-year 2025 --end-month 10\n"
                    "   ```"
                )
            else:
                status_placeholder.error(f"❌ **Ingestion failed:** {error_msg}\n\nCheck logs for details.")
            
            st.session_state.ingestion_running = False
            
            # Show refresh button instead of auto-refresh
            if st.button("🔄 Refresh Statistics & Close", key="refresh_after_error"):
                st.rerun()
    
    st.divider()
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Statistics"):
            st.rerun()
    
    with col2:
        if st.button("📥 Update Recent Data"):
            st.info("💡 Use the update script: `uv run python scripts/update_database.py`")
    
    # Validation Section
    st.divider()
    st.subheader("✅ Data Validation")
    
    if st.button("🔍 Validate Database"):
        try:
            import subprocess
            result = subprocess.run(
                ["uv", "run", "python", "scripts/validate_data.py"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                st.success("✅ Database validation passed!")
                st.code(result.stdout)
            else:
                output = result.stdout + result.stderr
                if "Database is locked" in output or "Conflicting lock" in output:
                    st.warning("⚠️ Database is locked")
                    st.info(
                        "The database cannot be validated while the Streamlit app is running.\n\n"
                        "**To validate the database:**\n"
                        "1. Stop the Streamlit app (the app must be stopped)\n"
                        "2. Run validation from the command line:\n"
                        "   ```bash\n"
                        "   uv run python scripts/validate_data.py\n"
                        "   ```\n"
                        "3. Restart the Streamlit app after validation"
                    )
                    st.code(output)
                else:
                    st.warning("⚠️ Database validation found issues:")
                    st.code(output)
        except subprocess.TimeoutExpired:
            st.error("⚠️ Validation timed out. Try running from command line instead.")
        except Exception as e:
            st.error(f"Failed to run validation: {e}")
            st.info(
                "**Tip:** If you see a database lock error, stop the Streamlit app "
                "and run validation from the command line:\n"
                "```bash\n"
                "uv run python scripts/validate_data.py\n"
                "```"
            )

