"""API client for GBIF (Global Biodiversity Information Facility) API."""
import httpx
from typing import Dict, List, Optional, Any
from datetime import date


class GBIFAPIClient:
    """Client for interacting with the GBIF API to access Swedish bird observations."""

    def __init__(self, base_url: str, dataset_key: str):
        """
        Initialize the GBIF API client.

        Args:
            base_url: Base URL for the GBIF API
            dataset_key: Dataset key for the Artportalen dataset
        """
        self.base_url = base_url.rstrip('/')
        self.dataset_key = dataset_key
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "BirdingVibing/1.0 (Swedish Bird Observations App)"
        }

    def search_occurrences(
        self,
        taxon_key: Optional[int] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        month: Optional[int] = None,
        country: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        state_province: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for bird observations in the dataset.

        Args:
            taxon_key: GBIF taxon key (e.g., 212 for all birds/Aves)
            start_year: Start year for observations
            end_year: End year for observations
            month: Month filter (1-12)
            country: ISO country code (e.g., 'SE' for Sweden)
            limit: Maximum number of results to return (max 300)
            offset: Offset for pagination
            state_province: State or province name filter

        Returns:
            Dict containing search results and metadata
        """
        endpoint = f"{self.base_url}/occurrence/search"

        # Build query parameters
        params = {
            "datasetKey": self.dataset_key,
            "limit": min(limit, 300),  # GBIF max is 300 per request
            "offset": offset
        }

        if taxon_key:
            params["taxonKey"] = taxon_key

        if start_year:
            params["year"] = f"{start_year},{end_year if end_year else start_year}"

        if month:
            params["month"] = month

        if country:
            params["country"] = country

        if state_province:
            params["stateProvince"] = state_province

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(endpoint, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "results": [],
                "count": 0
            }
        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}",
                "results": [],
                "count": 0
            }

    def get_dataset_info(self) -> Dict[str, Any]:
        """
        Get information about the dataset.

        Returns:
            Dict containing dataset information
        """
        endpoint = f"{self.base_url}/dataset/{self.dataset_key}"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}"
            }

    def get_species_info(self, taxon_key: int) -> Dict[str, Any]:
        """
        Get information about a specific species/taxon.

        Args:
            taxon_key: GBIF taxon key

        Returns:
            Dict containing taxon information
        """
        endpoint = f"{self.base_url}/species/{taxon_key}"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}"
            }

    def search_species(
        self,
        query: str,
        rank: Optional[str] = None,
        highertaxon_key: Optional[int] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for species by name.

        Args:
            query: Search query (species name)
            rank: Taxonomic rank filter (e.g., 'SPECIES', 'GENUS')
            highertaxon_key: Filter by higher taxon (e.g., 212 for birds)
            limit: Maximum number of results

        Returns:
            Dict containing search results
        """
        endpoint = f"{self.base_url}/species/search"

        params = {
            "q": query,
            "limit": limit
        }

        if rank:
            params["rank"] = rank

        if highertaxon_key:
            params["highertaxonKey"] = highertaxon_key

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                "error": f"Search failed: {str(e)}",
                "results": []
            }
