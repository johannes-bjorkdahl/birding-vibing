"""Unified API client that selects between Artportalen and GBIF APIs based on date range."""
from typing import Dict, Optional, Any, Literal
from datetime import date, timedelta

from src.api.gbif_client import GBIFAPIClient
from src.api.artportalen_client import ArtportalenAPIClient
from src.api.data_adapter import normalize_artportalen_response
from src.config import Config


class UnifiedAPIClient:
    """
    Unified client that automatically selects the appropriate API based on date range.
    
    - Recent dates (within threshold) → Artportalen API (real-time)
    - Historical dates (older) → GBIF API (weekly updates)
    - Fallback to GBIF if Artportalen unavailable/unauthenticated
    """

    def __init__(
        self,
        gbif_client: GBIFAPIClient,
        artportalen_client: Optional[ArtportalenAPIClient] = None,
        date_threshold_days: int = 7
    ):
        """
        Initialize the unified API client.

        Args:
            gbif_client: GBIF API client instance
            artportalen_client: Artportalen API client instance (optional)
            date_threshold_days: Number of days threshold for API selection
        """
        self.gbif_client = gbif_client
        self.artportalen_client = artportalen_client
        self.date_threshold_days = date_threshold_days

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
        use_artportalen, reason = self._should_use_artportalen(
            start_date, end_date, force_api
        )

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
                    normalized["_api_selection_reason"] = reason
                    return normalized
                else:
                    # If Artportalen fails, fallback to GBIF
                    error_msg = result.get("error", "Unknown error")
                    # Continue to GBIF fallback below
                    use_artportalen = False
                    reason = f"artportalen_failed: {error_msg}"

            except Exception as e:
                # Exception occurred, fallback to GBIF
                use_artportalen = False
                reason = f"artportalen_exception: {str(e)}"

        # Use GBIF API (default or fallback)
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

        # Add API source indicator
        if "error" not in result:
            result["_api_source"] = "gbif"
            result["_api_selection_reason"] = reason
        else:
            result["_api_source"] = "gbif"
            result["_api_selection_reason"] = reason

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
            "date_threshold_days": self.date_threshold_days
        }

