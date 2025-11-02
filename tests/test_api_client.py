"""Tests for GBIF API client filtering functionality."""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch
import httpx
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.gbif_client import GBIFAPIClient
from src.config import Config


class TestDateRangeFiltering:
    """Test date range filtering functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GBIFAPIClient(
            base_url="https://api.gbif.org/v1",
            dataset_key=Config.DATASET_KEY
        )

    @patch('src.api.gbif_client.httpx.Client')
    def test_date_range_filtering(self, mock_client_class):
        """Test that date range is correctly formatted in API request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [],
            "count": 0
        }
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        # Test date range
        start_date = date(2024, 10, 30)
        end_date = date(2024, 10, 31)
        
        self.client.search_occurrences(
            taxon_key=212,
            start_date=start_date,
            end_date=end_date,
            country="SE"
        )

        # Verify the API was called
        assert mock_client.get.called
        
        # Get the call arguments
        call_args = mock_client.get.call_args
        assert call_args is not None
        
        # Check that eventDate parameter is correctly formatted
        params = call_args.kwargs['params']
        assert 'eventDate' in params
        assert params['eventDate'] == "2024-10-30,2024-10-31"

    @patch('src.api.gbif_client.httpx.Client')
    def test_single_date_filtering(self, mock_client_class):
        """Test that single date is correctly formatted."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        single_date = date(2024, 10, 31)
        
        self.client.search_occurrences(
            taxon_key=212,
            start_date=single_date,
            country="SE"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert 'eventDate' in params
        assert params['eventDate'] == "2024-10-31,2024-10-31"

    @patch('src.api.gbif_client.httpx.Client')
    def test_default_date_range_yesterday_today(self, mock_client_class):
        """Test that default date range uses yesterday and today."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        today = date.today()
        yesterday = today - timedelta(days=1)
        
        self.client.search_occurrences(
            taxon_key=212,
            start_date=yesterday,
            end_date=today,
            country="SE"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert 'eventDate' in params
        
        # Verify the date range spans exactly 2 days (yesterday and today)
        date_range = params['eventDate'].split(',')
        assert len(date_range) == 2
        start, end = date_range
        start_date_obj = date.fromisoformat(start)
        end_date_obj = date.fromisoformat(end)
        
        assert (end_date_obj - start_date_obj).days == 1  # Exactly 1 day difference

    @patch('src.api.gbif_client.httpx.Client')
    def test_date_range_with_multiple_days(self, mock_client_class):
        """Test date range spanning multiple days."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        start_date = date(2024, 10, 1)
        end_date = date(2024, 10, 7)
        
        self.client.search_occurrences(
            taxon_key=212,
            start_date=start_date,
            end_date=end_date,
            country="SE"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert params['eventDate'] == "2024-10-01,2024-10-07"

    @patch('src.api.gbif_client.httpx.Client')
    def test_date_range_crosses_month_boundary(self, mock_client_class):
        """Test date range that crosses month boundary."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        start_date = date(2024, 9, 30)
        end_date = date(2024, 10, 2)
        
        self.client.search_occurrences(
            taxon_key=212,
            start_date=start_date,
            end_date=end_date,
            country="SE"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert params['eventDate'] == "2024-09-30,2024-10-02"


class TestLocationFiltering:
    """Test location filtering functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GBIFAPIClient(
            base_url="https://api.gbif.org/v1",
            dataset_key=Config.DATASET_KEY
        )

    @patch('src.api.gbif_client.httpx.Client')
    def test_state_province_filtering(self, mock_client_class):
        """Test that state/province filter is included in API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE",
            state_province="Skåne"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert 'stateProvince' in params
        assert params['stateProvince'] == "Skåne"

    @patch('src.api.gbif_client.httpx.Client')
    def test_locality_filtering(self, mock_client_class):
        """Test that locality filter is included in API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE",
            locality="Stockholm"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert 'locality' in params
        assert params['locality'] == "Stockholm"

    @patch('src.api.gbif_client.httpx.Client')
    def test_combined_location_filters(self, mock_client_class):
        """Test combining state/province and locality filters."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE",
            state_province="Stockholm",
            locality="Södermalm"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert 'stateProvince' in params
        assert 'locality' in params
        assert params['stateProvince'] == "Stockholm"
        assert params['locality'] == "Södermalm"

    @patch('src.api.gbif_client.httpx.Client')
    def test_no_location_filters_when_none_provided(self, mock_client_class):
        """Test that location parameters are not included when None."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE",
            state_province=None,
            locality=None
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        assert 'stateProvince' not in params
        assert 'locality' not in params


class TestCombinedFilters:
    """Test combining date and location filters."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GBIFAPIClient(
            base_url="https://api.gbif.org/v1",
            dataset_key=Config.DATASET_KEY
        )

    @patch('src.api.gbif_client.httpx.Client')
    def test_date_and_location_filters_together(self, mock_client_class):
        """Test that date and location filters work together."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE",
            state_province="Skåne",
            locality="Malmö"
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs['params']
        
        # Verify all filters are present
        assert 'eventDate' in params
        assert 'stateProvince' in params
        assert 'locality' in params
        assert params['eventDate'] == "2024-10-30,2024-10-31"
        assert params['stateProvince'] == "Skåne"
        assert params['locality'] == "Malmö"

    @patch('src.api.gbif_client.httpx.Client')
    def test_response_structure_handling(self, mock_client_class):
        """Test that API response structure is handled correctly."""
        # Test with proper GBIF response structure
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "key": 12345,
                    "species": "Parus major",
                    "eventDate": "2024-10-30"
                }
            ],
            "count": 1
        }
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        result = self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE"
        )

        assert 'results' in result
        assert 'count' in result
        assert result['count'] == 1
        assert len(result['results']) == 1

    @patch('src.api.gbif_client.httpx.Client')
    def test_response_with_missing_fields(self, mock_client_class):
        """Test handling of API response with missing fields."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": []
            # Missing 'count' field
        }
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        result = self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE"
        )

        # Should handle missing count field gracefully
        assert 'results' in result
        assert 'count' in result
        assert result['count'] == 0

    @patch('src.api.gbif_client.httpx.Client')
    def test_error_handling(self, mock_client_class):
        """Test error handling in API calls."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=Mock(status_code=404, text="Not found")
        )
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        result = self.client.search_occurrences(
            taxon_key=212,
            start_date=date(2024, 10, 30),
            end_date=date(2024, 10, 31),
            country="SE"
        )

        assert 'error' in result
        assert 'results' in result
        assert 'count' in result
        assert result['count'] == 0

