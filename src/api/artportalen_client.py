"""API client for Artportalen (Swedish Species Observation System) API."""
import httpx
from typing import Dict, List, Optional, Any
from datetime import date, datetime


class ArtportalenAPIClient:
    """
    Client for interacting with the Artportalen API to access real-time bird observations.
    
    IMPORTANT API FORMAT REQUIREMENTS:
    - Date filters MUST use nested format: {"date": {"startDate": "...", "endDate": "...", "dateFilterType": "..."}}
    - Taxon filters MUST use nested format: {"taxon": {"ids": [...]}}
    - Do NOT use flat parameters like "dateFrom"/"dateTo" or "taxonIds"
    
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
                "error": "Artportalen API key not configured. Please set ARTPORTALEN_SLU_API_KEY in .env file.",
                "results": [],
                "count": 0
            }

        # Artportalen API endpoint - correct endpoint for searching observations
        endpoint = f"{self.base_url}/Observations/Search"

        # Build request body (Artportalen likely uses POST with JSON body)
        # Note: Artportalen API doesn't reliably filter by date server-side,
        # so when date filters are specified, we request more records to increase
        # chances of finding matches (since API returns records from various dates)
        request_limit = min(limit, 1000)  # API max is 1000
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
        if taxon_id:
            request_body["taxon"] = {"ids": [taxon_id]}

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
                            
                            # Copy filters from original request
                            if taxon_id:
                                next_request_body["taxon"] = {"ids": [taxon_id]}
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
                            if state_province:
                                next_request_body["province"] = state_province
                            if locality:
                                next_request_body["locality"] = locality
                            
                            with httpx.Client(timeout=30.0) as client:
                                next_response = client.post(
                                    endpoint,
                                    json=next_request_body,
                                    headers=self.headers
                                )
                                next_response.raise_for_status()
                                next_data = next_response.json()
                                
                                # Get records from next batch
                                if isinstance(next_data, dict) and "records" in next_data:
                                    next_batch_records = next_data.get("records", [])
                                    if not next_batch_records:
                                        break  # No more records
                                    
                                    # Filter this batch and add to results
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

