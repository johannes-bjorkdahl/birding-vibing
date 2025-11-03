"""Unified API client that selects between DuckDB, Artportalen, and GBIF APIs based on date range."""
from typing import Dict, Optional, Any, Literal
from datetime import date, timedelta
import logging

from src.api.gbif_client import GBIFAPIClient
from src.api.artportalen_client import ArtportalenAPIClient
from src.api.data_adapter import normalize_artportalen_response
from src.config import Config

logger = logging.getLogger(__name__)

# Try to import database components (may not be available)
try:
    from src.database import DuckDBConnection, DatabaseQueryClient, validate_schema
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("Database module not available - database queries will be disabled")


class UnifiedAPIClient:
    """
    Unified client that automatically selects the appropriate data source based on date range.
    
    Routing logic:
    - Historical dates (older than database threshold, default 30 days) → DuckDB (if available)
    - Recent dates (within threshold) → Artportalen API (real-time)
    - Fallback: DuckDB → Artportalen → GBIF
    - Mixed date ranges → Query both database and API, merge results
    """

    def __init__(
        self,
        gbif_client: GBIFAPIClient,
        artportalen_client: Optional[ArtportalenAPIClient] = None,
        date_threshold_days: int = 7,
        database_path: Optional[str] = None,
        use_database: bool = True
    ):
        """
        Initialize the unified API client.

        Args:
            gbif_client: GBIF API client instance
            artportalen_client: Artportalen API client instance (optional)
            date_threshold_days: Number of days threshold for Artportalen API selection
            database_path: Path to DuckDB database file (optional, uses Config default)
            use_database: Enable database usage (default: True)
        """
        self.gbif_client = gbif_client
        self.artportalen_client = artportalen_client
        self.date_threshold_days = date_threshold_days
        self.use_database = use_database and DATABASE_AVAILABLE
        
        # Initialize database client if available
        self.database_client = None
        self.database_available = False
        
        if self.use_database:
            try:
                db_path = database_path or Config.DATABASE_PATH
                db_connection = DuckDBConnection(db_path)
                
                # Check if database schema exists and is valid
                if validate_schema(db_connection.connection):
                    self.database_client = DatabaseQueryClient(db_connection.connection)
                    self.database_available = True
                    logger.info(f"Database client initialized: {db_path}")
                else:
                    logger.warning(f"Database exists but schema is invalid: {db_path}")
                    self.database_available = False
            except Exception as e:
                # Database initialization failed - disable database but continue with API fallback
                logger.warning(f"Could not initialize database client: {e}")
                logger.info("Continuing without database - using API fallback")
                self.database_available = False
                self.use_database = False  # Disable database for this session

    def _should_use_database(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        force_api: Optional[Literal["auto", "artportalen", "gbif"]] = None
    ) -> tuple[bool, str]:
        """
        Determine if database should be used for this query.
        
        Args:
            start_date: Start date of query
            end_date: End date of query
            force_api: Force API selection (if not "auto", database is not used)
            
        Returns:
            Tuple of (use_database: bool, reason: str)
        """
        # Database disabled or not available
        if not self.use_database or not self.database_available:
            return False, "database_unavailable"
        
        # Manual API override
        if force_api and force_api != "auto":
            return False, "manual_api_selection"
        
        # If no dates provided, don't use database (use API)
        if not start_date and not end_date:
            return False, "no_date_range"
        
        # Check if date range is historical (older than database threshold)
        today = date.today()
        database_threshold_days = Config.DATABASE_DATE_THRESHOLD_DAYS
        
        # Use end_date or start_date to determine recency
        check_date = end_date if end_date else start_date
        
        if check_date:
            days_ago = (today - check_date).days
            
            # If date range is older than threshold, use database
            if days_ago > database_threshold_days:
                return True, "historical_date_range"
        
        return False, "recent_date_range"
    
    def _should_use_artportalen(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        force_api: Optional[Literal["auto", "artportalen", "gbif"]] = None
    ) -> tuple[bool, str]:
        """
        Determine which API to use based on date range.

        Args:
            start_date: Start date of query
            end_date: End date of query
            force_api: Force API selection ("auto", "artportalen", or "gbif")

        Returns:
            Tuple of (use_artportalen: bool, reason: str)
        """
        # Manual override
        if force_api == "gbif":
            return False, "manual_selection"
        if force_api == "artportalen":
            if not self.artportalen_client or not self.artportalen_client._is_authenticated():
                return False, "artportalen_unavailable"
            return True, "manual_selection"

        # Check if Artportalen client is available
        if not self.artportalen_client or not self.artportalen_client._is_authenticated():
            return False, "artportalen_unavailable"

        # If no dates provided, use GBIF (safer default)
        if not start_date and not end_date:
            return False, "no_date_range"

        # Use end_date or start_date to determine recency
        today = date.today()
        check_date = end_date if end_date else start_date

        if check_date:
            days_ago = (today - check_date).days
            
            # If any part of the range is recent, prefer Artportalen
            if days_ago <= self.date_threshold_days:
                return True, "recent_date_range"
            else:
                return False, "historical_date_range"

        return False, "unknown"

    def search_occurrences(
        self,
        taxon_key: Optional[int] = None,
        taxon_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        state_province: Optional[str] = None,
        locality: Optional[str] = None,
        force_api: Optional[Literal["auto", "artportalen", "gbif"]] = "auto"
    ) -> Dict[str, Any]:
        """
        Search for occurrences using the appropriate API.

        Args:
            taxon_key: GBIF taxon key (for GBIF API)
            taxon_id: Artportalen taxon ID (for Artportalen API)
            start_date: Start date for observations
            end_date: End date for observations
            country: ISO country code
            limit: Maximum number of results
            offset: Offset for pagination
            state_province: State or province filter
            locality: Locality filter
            force_api: Force API selection ("auto", "artportalen", or "gbif")

        Returns:
            Dict containing search results with _api_source indicator
        """
        # Check if we should use database
        use_database, db_reason = self._should_use_database(
            start_date, end_date, force_api
        )
        
        # Check if we should use Artportalen
        use_artportalen, api_reason = self._should_use_artportalen(
            start_date, end_date, force_api
        )
        
        # Initialize reason variable early to avoid UnboundLocalError
        reason = api_reason
        
        # Determine if we have a mixed date range (both historical and recent)
        has_mixed_range = False
        if start_date and end_date:
            today = date.today()
            database_threshold = Config.DATABASE_DATE_THRESHOLD_DAYS
            start_days_ago = (today - start_date).days
            end_days_ago = (today - end_date).days
            
            # Mixed if start is historical and end is recent, or vice versa
            if (start_days_ago > database_threshold and end_days_ago <= database_threshold) or \
               (start_days_ago <= database_threshold and end_days_ago > database_threshold):
                has_mixed_range = True
        
        # Try database first for historical queries
        if use_database and not has_mixed_range:
            try:
                result = self.database_client.search_occurrences(
                    taxon_key=taxon_key,
                    taxon_id=taxon_id,
                    start_date=start_date,
                    end_date=end_date,
                    country=country,
                    limit=limit,
                    offset=offset,
                    state_province=state_province,
                    locality=locality,
                    force_api=force_api
                )
                
                if "error" not in result:
                    result["_api_selection_reason"] = db_reason
                    return result
                else:
                    logger.warning(f"Database query failed: {result.get('error')}, falling back to API")
            except Exception as e:
                logger.warning(f"Database query exception: {e}, falling back to API")
        
        # Handle mixed date ranges: query both database and API
        if has_mixed_range and use_database:
            try:
                # Split date range: historical part from database, recent part from API
                today = date.today()
                database_threshold = Config.DATABASE_DATE_THRESHOLD_DAYS
                threshold_date = today - timedelta(days=database_threshold)
                
                # Determine historical and recent portions
                if start_date and end_date:
                    if start_date < threshold_date and end_date > threshold_date:
                        # Mixed range: query database for historical, API for recent
                        db_start = start_date
                        db_end = threshold_date
                        api_start = threshold_date + timedelta(days=1)
                        api_end = end_date
                        
                        # Query database for historical portion
                        # Request more records to account for merging and offset
                        db_limit = limit + offset if offset else limit
                        db_result = self.database_client.search_occurrences(
                            taxon_key=taxon_key,
                            taxon_id=taxon_id,
                            start_date=db_start,
                            end_date=db_end,
                            country=country,
                            limit=db_limit,
                            offset=0,  # Reset offset for database query
                            state_province=state_province,
                            locality=locality
                        )
                        
                        # Query API for recent portion
                        api_limit = limit + offset if offset else limit
                        api_result = None
                        if use_artportalen:
                            api_result = self.artportalen_client.search_occurrences(
                                taxon_id=taxon_id,
                                start_date=api_start,
                                end_date=api_end,
                                country=country,
                                limit=api_limit,
                                offset=0,
                                state_province=state_province,
                                locality=locality
                            )
                        
                        if not api_result or "error" in api_result:
                            # Fallback to GBIF if Artportalen fails
                            api_result = self.gbif_client.search_occurrences(
                                taxon_key=taxon_key,
                                start_date=api_start,
                                end_date=api_end,
                                country=country,
                                limit=limit,
                                offset=0,
                                state_province=state_province,
                                locality=locality
                            )
                        
                        # Merge results (database results first, then API results)
                        merged_results = []
                        merged_count = 0
                        
                        if "error" not in db_result:
                            db_results = db_result.get("results", [])
                            merged_results.extend(db_results)
                            merged_count += db_result.get("count", 0)
                        
                        if "error" not in api_result:
                            api_results = api_result.get("results", [])
                            merged_results.extend(api_results)
                            merged_count += api_result.get("count", 0)
                        
                        # Sort by date (most recent first) to match API behavior
                        merged_results.sort(
                            key=lambda x: x.get("eventDate") or x.get("year", 0) * 10000 + x.get("month", 0) * 100 + x.get("day", 0),
                            reverse=True
                        )
                        
                        # Apply offset and limit to merged results
                        if offset:
                            merged_results = merged_results[offset:]
                        if limit:
                            merged_results = merged_results[:limit]
                        
                        return {
                            "results": merged_results,
                            "count": merged_count,
                            "_api_source": "mixed",
                            "_api_selection_reason": f"mixed_range: database({db_reason}) + api({api_reason})"
                        }
            except Exception as e:
                logger.warning(f"Mixed range query failed: {e}, falling back to API only")
        
        # Try Artportalen if selected
        if use_artportalen:
            try:
                result = self.artportalen_client.search_occurrences(
                    taxon_id=taxon_id,
                    start_date=start_date,
                    end_date=end_date,
                    country=country,
                    limit=limit,
                    offset=offset,
                    state_province=state_province,
                    locality=locality
                )

                # If successful, normalize and return
                if "error" not in result:
                    normalized = normalize_artportalen_response(result)
                    normalized["_api_source"] = "artportalen"
                    normalized["_api_selection_reason"] = api_reason
                    return normalized
                else:
                    # If Artportalen fails, preserve error and fallback to GBIF
                    error_msg = result.get("error", "Unknown error")
                    # Continue to GBIF fallback below
                    use_artportalen = False
                    reason = f"artportalen_failed: {error_msg}"

            except Exception as e:
                # Exception occurred, preserve error and fallback to GBIF
                use_artportalen = False
                reason = f"artportalen_exception: {str(e)}"

        # Use GBIF API (default or fallback)
        # reason should already be set, but ensure it's set for GBIF fallback
        if not use_artportalen and reason == api_reason:
            # If we're going straight to GBIF (not falling back from Artportalen), 
            # reason should reflect that
            _, reason = self._should_use_artportalen(start_date, end_date, force_api)
        
        result = self.gbif_client.search_occurrences(
            taxon_key=taxon_key,
            start_date=start_date,
            end_date=end_date,
            country=country,
            limit=limit,
            offset=offset,
            state_province=state_province,
            locality=locality
        )

        # Add API source indicator and preserve Artportalen error if it failed
        if "error" not in result:
            result["_api_source"] = "gbif"
            result["_api_selection_reason"] = reason
            # If we fell back from Artportalen, include the error info
            if reason.startswith("artportalen_failed") or reason.startswith("artportalen_exception"):
                result["_artportalen_error"] = reason.split(":", 1)[1] if ":" in reason else reason
        else:
            result["_api_source"] = "gbif"
            result["_api_selection_reason"] = reason
            # Preserve Artportalen error even if GBIF also fails
            if reason.startswith("artportalen_failed") or reason.startswith("artportalen_exception"):
                result["_artportalen_error"] = reason.split(":", 1)[1] if ":" in reason else reason

        return result

    def get_current_api_info(self) -> Dict[str, Any]:
        """
        Get information about current API configuration.

        Returns:
            Dict with API availability and configuration info
        """
        return {
            "gbif_available": True,
            "artportalen_available": (
                self.artportalen_client is not None and
                self.artportalen_client._is_authenticated()
            ),
            "database_available": self.database_available,
            "date_threshold_days": self.date_threshold_days,
            "database_threshold_days": Config.DATABASE_DATE_THRESHOLD_DAYS
        }

