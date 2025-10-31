"""API client for Artdatabanken Species Observation System."""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import time


class ArtdatabankenAPIClient:
    """Client for interacting with the Artdatabanken Species Observation System API."""

    def __init__(self, api_key: str, base_url: str):
        """
        Initialize the API client.

        Args:
            api_key: API subscription key from Artdatabanken
            base_url: Base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def search_observations(
        self,
        taxon_ids: Optional[List[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        province: Optional[str] = None,
        max_results: int = 100,
        output_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for bird observations.

        Args:
            taxon_ids: List of taxon IDs to search for (e.g., [4000104] for all birds)
            start_date: Start date for observations
            end_date: End date for observations
            province: Swedish province name to filter by
            max_results: Maximum number of results to return
            output_fields: List of fields to include in the output

        Returns:
            Dict containing search results and metadata
        """
        endpoint = f"{self.base_url}/Observations/Search"

        # Build the search filter
        search_filter = {}

        if taxon_ids:
            search_filter["taxon"] = {
                "ids": taxon_ids,
                "includeUnderlyingTaxa": True
            }

        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["startDate"] = start_date.isoformat()
            if end_date:
                date_filter["endDate"] = end_date.isoformat()
            search_filter["date"] = date_filter

        if province:
            search_filter["location"] = {
                "areas": [{"featureId": province}]
            }

        # Build the request payload
        payload = {
            "filter": search_filter,
            "skip": 0,
            "take": min(max_results, 1000)  # API usually has limits
        }

        if output_fields:
            payload["outputFields"] = output_fields

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "records": []
            }
        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}",
                "records": []
            }

    def get_taxon_info(self, taxon_id: int) -> Dict[str, Any]:
        """
        Get information about a specific taxon.

        Args:
            taxon_id: The taxon ID to look up

        Returns:
            Dict containing taxon information
        """
        endpoint = f"{self.base_url}/Taxa/{taxon_id}"

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

    def export_observations_csv(
        self,
        taxon_ids: Optional[List[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        output_fields: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Request a CSV export of observations. This is an async operation.

        Args:
            taxon_ids: List of taxon IDs to export
            start_date: Start date for observations
            end_date: End date for observations
            output_fields: List of fields to include in the export

        Returns:
            Job ID for tracking the export, or None if failed
        """
        endpoint = f"{self.base_url}/Exports/Order/Csv"

        # Build the export filter (similar to search)
        export_filter = {}

        if taxon_ids:
            export_filter["taxon"] = {
                "ids": taxon_ids,
                "includeUnderlyingTaxa": True
            }

        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["startDate"] = start_date.isoformat()
            if end_date:
                date_filter["endDate"] = end_date.isoformat()
            export_filter["date"] = date_filter

        payload = {"filter": export_filter}

        if output_fields:
            payload["outputFields"] = output_fields

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                return result.get("jobId")
        except Exception as e:
            print(f"Export request failed: {e}")
            return None

    def check_export_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of an export job.

        Args:
            job_id: The job ID returned from export_observations_csv

        Returns:
            Dict containing job status and download URL if ready
        """
        endpoint = f"{self.base_url}/Jobs/{job_id}/Status"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                "error": f"Status check failed: {str(e)}"
            }
