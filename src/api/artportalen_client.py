"""API client for Artportalen (Swedish Species Observation System) API."""
import httpx
import time
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from src.locations import get_area_filter


class ArtportalenAPIClient:
    """
    Client for interacting with the Artportalen API to access real-time bird observations.
    
    IMPORTANT API FORMAT REQUIREMENTS:
    - Date filters MUST use nested format: {"date": {"startDate": "...", "endDate": "...", "dateFilterType": "..."}}
    - Taxon filters MUST use nested format: {"taxon": {"ids": [...]}}
    - Location filters MUST use nested format: {"geographics": {"areas": [{"areaType": "...", "featureId": "..."}]}}
    - Do NOT use flat parameters like "dateFrom"/"dateTo", "taxonIds", or "province"/"locality"
    
    For API documentation and troubleshooting:
    - See docs/API_TROUBLESHOOTING.md for complete guide
    - GitHub: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/SearchFilter.md
    - API Info: https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo
    """

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
                "error": "Artportalen API key not configured. Please set ARTPORTALEN_SLU_API_KEY in .streamlit/secrets.toml file (recommended) or as an environment variable.",
                "results": [],
                "count": 0
            }

        # Artportalen API endpoint - correct endpoint for searching observations
        endpoint = f"{self.base_url}/Observations/Search"

        # Build request body (Artportalen likely uses POST with JSON body)
        # Note: Artportalen API doesn't reliably filter by date server-side,
        # so when date filters are specified, we request more records to increase
        # chances of finding matches (since API returns records from various dates)
        # API limits per official documentation:
        # - Maximum page size: 1000 records per page
        # - Maximum total: 10,000 records per search query (skip + take cannot exceed 10,000)
        # Source: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/FAQ.md
        request_limit = min(limit, 1000)  # API max page size is 1000
        if start_date or end_date:
            # When filtering by date, request more records since API doesn't filter server-side
            # This increases probability of finding records in the specified date range
            # Request at least 100 records, or 10x the requested limit, whichever is smaller
            request_limit = min(max(limit * 10, 100), 1000)
        
        request_body = {
            "skip": offset,
            "take": request_limit,
        }

        # Add filters
        # NOTE: Artportalen API requires nested objects, not flat parameters
        # See docs/API_TROUBLESHOOTING.md for details
        # NOTE: We don't use taxon filter here because taxon_id parameter might be incorrect
        # (e.g., 100012 is gråhäger, not all birds). Instead, we filter client-side
        # to only include bird observations based on the taxon information in responses.
        # If a taxon_id is provided, it will be ignored and all observations will be returned,
        # then filtered client-side for birds only.

        # Date filter - use nested date object with startDate/endDate (correct API format)
        # Format: {"date": {"startDate": "...", "endDate": "...", "dateFilterType": "..."}}
        # Do NOT use "dateFrom"/"dateTo" - that's the old (incorrect) format
        if start_date and end_date:
            request_body["date"] = {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dateFilterType": "OverlappingStartDateAndEndDate"  # Default filter type
            }
        elif start_date:
            request_body["date"] = {
                "startDate": start_date.isoformat(),
                "endDate": start_date.isoformat(),
                "dateFilterType": "OverlappingStartDateAndEndDate"
            }

        if country:
            request_body["country"] = country

        # Location filter - use nested geographics object with areas array (correct API format)
        # Format: {"geographics": {"areas": [{"areaType": "County"|"Municipality", "featureId": "..."}]}}
        # Do NOT use flat "province"/"locality" parameters - that's the old (incorrect) format
        geographics_filter = get_area_filter(state_province=state_province, locality=locality)
        if geographics_filter:
            request_body.update(geographics_filter)

        try:
            with httpx.Client(timeout=60.0) as client:  # Increased timeout to 60 seconds
                # Try POST first (common for search endpoints with filters)
                # Add retry logic for rate limiting (429 errors)
                max_retries = 5
                retry_delay = 1.0  # Start with 1 second delay
                
                for attempt in range(max_retries):
                    try:
                        response = client.post(
                            endpoint,
                            json=request_body,
                            headers=self.headers
                        )
                        
                        # Handle 429 rate limit errors with exponential backoff
                        if response.status_code == 429:
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                                time.sleep(wait_time)
                                continue
                            else:
                                # Last attempt failed, raise the error
                                response.raise_for_status()
                        
                        response.raise_for_status()
                        data = response.json()
                        break  # Success, exit retry loop
                        
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
                            # Note: GET fallback doesn't support geographics filter properly
                            # Location filters will be skipped if POST fails
                            # This is acceptable since POST is the primary method
                            params["skip"] = offset
                            params["take"] = min(limit, 1000)
                            
                            response = client.get(endpoint, params=params, headers=self.headers)
                            response.raise_for_status()
                            data = response.json()
                        else:
                            raise

                # Normalize response structure
                # Artportalen API returns: {skip, take, totalCount, records}
                if isinstance(data, dict):
                    # Artportalen API returns records in 'records' field
                    if "records" in data:
                        normalized_data = {
                            "results": data.get("records", []),
                            "count": data.get("totalCount", len(data.get("records", [])))
                        }
                    elif "items" in data or "sightings" in data or "observations" in data:
                        # Handle other possible response patterns
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
                elif isinstance(data, list):
                    # If response is a list, wrap it
                    normalized_data = {
                        "results": data,
                        "count": len(data)
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

                # Filter for birds only (client-side filtering) - BEFORE normalization
                # Since taxon_id might be incorrect (e.g., 100012 is gråhäger, not all birds),
                # we filter client-side to only include bird observations.
                # Birds are identified by checking taxon.attributes.organismGroup == "Fåglar"
                if taxon_id:  # Only filter if taxon_id was requested (meaning we want birds only)
                    bird_results = []
                    raw_records = normalized_data.get('results', [])
                    
                    for record in raw_records:
                        is_bird = False
                        
                        # Check taxon information in raw record
                        taxon = record.get("taxon", {})
                        if isinstance(taxon, dict):
                            # Check attributes.organismGroup - most reliable indicator
                            attributes = taxon.get("attributes", {})
                            if isinstance(attributes, dict):
                                organism_group = attributes.get("organismGroup", "")
                                if organism_group == "Fåglar":  # Swedish for "Birds"
                                    is_bird = True
                            
                            # Fallback: Check if vernacular name contains "fågel" (bird in Swedish)
                            if not is_bird:
                                vernacular_name = taxon.get("vernacularName", "").lower()
                                if "fågel" in vernacular_name or "bird" in vernacular_name.lower():
                                    is_bird = True
                        
                        if is_bird:
                            bird_results.append(record)
                    
                    normalized_data['results'] = bird_results
                    normalized_data['count'] = len(bird_results)

                # Client-side date filtering (Artportalen API doesn't reliably filter by date)
                # Filter results by date range if dates were specified
                if start_date or end_date:
                    filtered_results = []
                    current_batch_records = normalized_data.get('results', [])
                    
                    # Helper function to filter records by date
                    def filter_records_by_date(records):
                        filtered = []
                        for record in records:
                            record_date = None
                            
                            # Extract date from event.startDate or event.endDate
                            if "event" in record and isinstance(record["event"], dict):
                                event_date_str = record["event"].get("startDate") or record["event"].get("endDate")
                                if event_date_str:
                                    try:
                                        # Parse ISO datetime string (e.g., "2025-11-01T00:00:00+02:00")
                                        # Extract just the date part (handle timezone indicators)
                                        date_part = event_date_str.split('T')[0].split('+')[0].split('-')
                                        if len(date_part) >= 3:
                                            record_date = datetime.strptime('-'.join(date_part[:3]), "%Y-%m-%d").date()
                                    except (ValueError, AttributeError, IndexError):
                                        pass
                            
                            # Check if record date is within range
                            if record_date:
                                date_in_range = True
                                if start_date and record_date < start_date:
                                    date_in_range = False
                                if end_date and record_date > end_date:
                                    date_in_range = False
                                
                                if date_in_range:
                                    filtered.append(record)
                        return filtered
                    
                    # Filter first batch
                    filtered_results.extend(filter_records_by_date(current_batch_records))
                    
                    # If we don't have enough filtered results, request more batches
                    # The API doesn't filter server-side, so we need to paginate through
                    # many records to find ones matching our date range
                    # Use a more efficient approach: sample from different offsets
                    # rather than sequential pagination, as records may be distributed
                    # throughout the dataset
                    max_batches_to_check = 200  # Check up to 200 batches
                    batch_size = 1000  # API max per request
                    
                    # Smart pagination: check batches with exponential backoff
                    # This helps find records faster if they're scattered
                    batches_checked = 0
                    checked_offsets = set()
                    
                    # Start with sequential batches, then sample more widely
                    for strategy_batch in range(max_batches_to_check):
                        if len(filtered_results) >= limit:
                            break
                        
                        # Calculate offset - mix sequential and sampling
                        if strategy_batch < 50:
                            # First 50 batches: sequential
                            next_offset = offset + (strategy_batch * batch_size)
                        elif strategy_batch < 100:
                            # Next 50: sample every 10k
                            next_offset = offset + ((strategy_batch - 50) * 10000)
                        else:
                            # Rest: sample every 100k
                            next_offset = offset + ((strategy_batch - 100) * 100000)
                        
                        if next_offset in checked_offsets:
                            continue
                        checked_offsets.add(next_offset)
                        
                        try:
                            # Request batch
                            next_request_body = {
                                "skip": next_offset,
                                "take": batch_size,
                            }
                            
                            # Copy filters from original request (but NOT taxon filter - we filter client-side)
                            if start_date and end_date:
                                next_request_body["date"] = {
                                    "startDate": start_date.isoformat(),
                                    "endDate": end_date.isoformat(),
                                    "dateFilterType": "OverlappingStartDateAndEndDate"
                                }
                            elif start_date:
                                next_request_body["date"] = {
                                    "startDate": start_date.isoformat(),
                                    "endDate": start_date.isoformat(),
                                    "dateFilterType": "OverlappingStartDateAndEndDate"
                                }
                            if country:
                                next_request_body["country"] = country
                            # Copy geographics filter from original request
                            geographics_filter = get_area_filter(state_province=state_province, locality=locality)
                            if geographics_filter:
                                next_request_body.update(geographics_filter)
                            
                            with httpx.Client(timeout=60.0) as client:  # Increased timeout to 60 seconds
                                # Add retry logic for rate limiting in batch requests
                                max_batch_retries = 3
                                batch_retry_delay = 1.0
                                
                                for batch_attempt in range(max_batch_retries):
                                    try:
                                        next_response = client.post(
                                            endpoint,
                                            json=next_request_body,
                                            headers=self.headers
                                        )
                                        
                                        # Handle 429 rate limit errors
                                        if next_response.status_code == 429:
                                            if batch_attempt < max_batch_retries - 1:
                                                wait_time = batch_retry_delay * (2 ** batch_attempt)
                                                time.sleep(wait_time)
                                                continue
                                            else:
                                                next_response.raise_for_status()
                                        
                                        next_response.raise_for_status()
                                        next_data = next_response.json()
                                        break  # Success, exit retry loop
                                    except httpx.HTTPStatusError as e:
                                        if batch_attempt == max_batch_retries - 1:
                                            raise  # Last attempt failed
                                        if e.response.status_code == 429:
                                            wait_time = batch_retry_delay * (2 ** batch_attempt)
                                            time.sleep(wait_time)
                                            continue
                                        raise
                                
                                # Get records from next batch
                                if isinstance(next_data, dict) and "records" in next_data:
                                    next_batch_records = next_data.get("records", [])
                                    if not next_batch_records:
                                        break  # No more records
                                    
                                    # Filter for birds if taxon_id was requested
                                    if taxon_id:
                                        bird_batch = []
                                        for record in next_batch_records:
                                            taxon = record.get("taxon", {})
                                            if isinstance(taxon, dict):
                                                attributes = taxon.get("attributes", {})
                                                if isinstance(attributes, dict):
                                                    organism_group = attributes.get("organismGroup", "")
                                                    if organism_group == "Fåglar":
                                                        bird_batch.append(record)
                                        next_batch_records = bird_batch
                                    
                                    # Filter this batch by date and add to results
                                    filtered_batch = filter_records_by_date(next_batch_records)
                                    filtered_results.extend(filtered_batch)
                                    batches_checked += 1
                                else:
                                    break  # No more records
                        except Exception:
                            # Continue to next batch on error
                            continue
                    
                    # Limit results to requested limit (after filtering)
                    filtered_results = filtered_results[:limit]
                    
                    # Update results and count
                    normalized_data['results'] = filtered_results
                    normalized_data['count'] = len(filtered_results)
                    # Note: totalCount from API may not reflect filtered count, but we update it
                    # to show the actual filtered count
                    
                    # If we have date filters but got few/no results, it might be because
                    # the API returned records outside the date range. The API doesn't support
                    # server-side date filtering, so we can only filter what we receive.

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

