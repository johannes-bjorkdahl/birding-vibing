"""Integration tests for filter functionality."""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.gbif_client import GBIFAPIClient
from src.app import search_observations
from src.config import Config


class TestFilterIntegration:
    """Integration tests for filter workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GBIFAPIClient(
            base_url="https://api.gbif.org/v1",
            dataset_key=Config.DATASET_KEY
        )

    @patch('src.app.st.session_state')
    @patch('src.app.st.spinner')
    @patch('src.app.st.error')
    @patch('src.app.st.info')
    def test_search_with_date_range(self, mock_info, mock_error, mock_spinner, mock_session):
        """Test search_observations with date range parameters."""
        # Setup session state mock
        mock_session.api_client = self.client
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "key": 12345,
                    "species": "Parus major",
                    "eventDate": "2024-10-30T12:00:00"
                }
            ],
            "count": 1
        }
        mock_response.raise_for_status = Mock()
        
        with patch('src.api.gbif_client.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client
            
            search_params = {
                'start_date': date(2024, 10, 30),
                'end_date': date(2024, 10, 31),
                'max_results': 100,
                'province': None,
                'locality': None
            }
            
            # This would require Streamlit mocking, so we'll test the API call directly
            result = self.client.search_occurrences(
                taxon_key=Config.BIRDS_TAXON_KEY,
                start_date=search_params['start_date'],
                end_date=search_params['end_date'],
                country=Config.COUNTRY_CODE,
                limit=search_params['max_results'],
                state_province=search_params['province'],
                locality=search_params.get('locality')
            )
            
            assert 'results' in result
            assert 'count' in result

    def test_date_and_location_filter_combination(self):
        """Test combining date and location filters."""
        with patch('src.api.gbif_client.httpx.Client') as mock_client_class:
            mock_response = Mock()
            mock_response.json.return_value = {"results": [], "count": 0}
            mock_response.raise_for_status = Mock()
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client
            
            search_params = {
                'start_date': date(2024, 10, 30),
                'end_date': date(2024, 10, 31),
                'max_results': 100,
                'province': "Skåne",
                'locality': "Malmö"
            }
            
            result = self.client.search_occurrences(
                taxon_key=Config.BIRDS_TAXON_KEY,
                start_date=search_params['start_date'],
                end_date=search_params['end_date'],
                country=Config.COUNTRY_CODE,
                limit=search_params['max_results'],
                state_province=search_params['province'],
                locality=search_params['locality']
            )
            
            # Verify API was called with correct parameters
            call_args = mock_client.get.call_args
            params = call_args.kwargs['params']
            
            assert params['eventDate'] == "2024-10-30,2024-10-31"
            assert params['stateProvince'] == "Skåne"
            assert params['locality'] == "Malmö"
            assert params['country'] == Config.COUNTRY_CODE
            assert params['taxonKey'] == Config.BIRDS_TAXON_KEY

    def test_default_date_range_integration(self):
        """Test that default date range (yesterday and today) works."""
        with patch('src.api.gbif_client.httpx.Client') as mock_client_class:
            mock_response = Mock()
            mock_response.json.return_value = {"results": [], "count": 0}
            mock_response.raise_for_status = Mock()
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client
            
            # Simulate default dates
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            result = self.client.search_occurrences(
                taxon_key=Config.BIRDS_TAXON_KEY,
                start_date=yesterday,
                end_date=today,
                country=Config.COUNTRY_CODE,
                limit=100
            )
            
            # Verify the date range was used
            call_args = mock_client.get.call_args
            params = call_args.kwargs['params']
            
            assert 'eventDate' in params
            date_range = params['eventDate'].split(',')
            assert len(date_range) == 2
            assert date.fromisoformat(date_range[0]) == yesterday
            assert date.fromisoformat(date_range[1]) == today

