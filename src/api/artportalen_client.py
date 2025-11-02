"""API client for Artportalen (Swedish Species Observation System) API."""
import httpx
from typing import Dict, List, Optional, Any
from datetime import date, datetime


class ArtportalenAPIClient:
    """Client for interacting with the Artportalen API to access real-time bird observations."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize the Artportalen API client.

        Args:
            base_url: Base URL for the Artportalen API
            api_key: API key for authentication (optional, but required for most endpoints)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "BirdingVibing/1.0 (Swedish Bird Observations App)"
        }
        
        # Add API key to headers if provided
        if self.api_key:
            self.headers["Ocp-Apim-Subscription-Key"] = self.api_key

    def _is_authenticated(self) -> bool:
        """Check if API key is available."""
        return self.api_key is not None and self.api_key.strip() != ""

    def search_occurrences(
        self,
        taxon_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        state_province: Optional[str] = None,
        locality: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for bird observations.

        Args:
            taxon_id: Artportalen taxon ID (e.g., 100012 for birds)
            start_date: Start date for observations (YYYY-MM-DD)
            end_date: End date for observations (YYYY-MM-DD)
            country: ISO country code (e.g., 'SE' for Sweden)
            limit: Maximum number of results to return
            offset: Offset for pagination
            state_province: State or province name filter
            locality: Locality (city/town) name filter

        Returns:
            Dict containing search results and metadata
        """
        if not self._is_authenticated():
            return {
                "error": "Artportalen API key not configured. Please set ARTPORTALEN_SLU_API_KEY in .env file.",
                "results": [],
                "count": 0
            }

        # Artportalen API endpoint - using common REST API pattern
        # This may need adjustment based on actual API documentation
        endpoint = f"{self.base_url}/Sightings/Search"

        # Build request body (Artportalen likely uses POST with JSON body)
        request_body = {
            "skip": offset,
            "take": min(limit, 1000),  # Reasonable max limit
        }

        # Add filters
        if taxon_id:
            request_body["taxonIds"] = [taxon_id]

        if start_date and end_date:
            # Format dates as ISO strings
            request_body["dateFrom"] = start_date.isoformat()
            request_body["dateTo"] = end_date.isoformat()
        elif start_date:
            request_body["dateFrom"] = start_date.isoformat()
            request_body["dateTo"] = start_date.isoformat()

        if country:
            request_body["country"] = country

        if state_province:
            request_body["province"] = state_province

        if locality:
            request_body["locality"] = locality

        try:
            with httpx.Client(timeout=30.0) as client:
                # Try POST first (common for search endpoints with filters)
                try:
                    response = client.post(
                        endpoint,
                        json=request_body,
                        headers=self.headers
                    )
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPStatusError as e:
                    # If POST fails, try GET with query parameters
                    if e.response.status_code == 405:  # Method Not Allowed
                        # Convert to query parameters
                        params = {}
                        if taxon_id:
                            params["taxonIds"] = str(taxon_id)
                        if start_date:
                            params["dateFrom"] = start_date.isoformat()
                        if end_date:
                            params["dateTo"] = end_date.isoformat()
                        if country:
                            params["country"] = country
                        if state_province:
                            params["province"] = state_province
                        if locality:
                            params["locality"] = locality
                        params["skip"] = offset
                        params["take"] = min(limit, 1000)
                        
                        response = client.get(endpoint, params=params, headers=self.headers)
                        response.raise_for_status()
                        data = response.json()
                    else:
                        raise

                # Normalize response structure
                # Artportalen API may return data in different formats
                # We'll handle common patterns here
                if isinstance(data, list):
                    # If response is a list, wrap it
                    normalized_data = {
                        "results": data,
                        "count": len(data)
                    }
                elif isinstance(data, dict):
                    # Check for common response patterns
                    if "items" in data or "sightings" in data or "observations" in data:
                        # Use the items/sightings/observations array
                        results_key = next(
                            (k for k in ["items", "sightings", "observations"] if k in data),
                            None
                        )
                        normalized_data = {
                            "results": data.get(results_key, []),
                            "count": data.get("totalCount", data.get("count", len(data.get(results_key, []))))
                        }
                    elif "results" in data:
                        # Already in expected format
                        normalized_data = data
                    else:
                        # Unknown format, try to extract results
                        normalized_data = {
                            "results": [],
                            "count": 0,
                            "raw": data  # Keep raw data for debugging
                        }
                else:
                    normalized_data = {
                        "results": [],
                        "count": 0,
                        "raw": data
                    }

                # Ensure we always return the expected structure
                if 'results' not in normalized_data:
                    normalized_data['results'] = []
                if 'count' not in normalized_data:
                    normalized_data['count'] = len(normalized_data.get('results', []))

                return normalized_data

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f": {error_detail}"
            except:
                error_msg += f": {e.response.text}"
            
            # Handle authentication errors specifically
            if e.response.status_code == 401 or e.response.status_code == 403:
                error_msg = "Artportalen API authentication failed. Please check your API key."
            
            return {
                "error": error_msg,
                "results": [],
                "count": 0
            }
        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}",
                "results": [],
                "count": 0
            }

