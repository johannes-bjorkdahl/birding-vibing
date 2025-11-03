"""Integration tests for UnifiedAPIClient with database integration."""
import pytest
import tempfile
import os
from datetime import date, timedelta
from src.database.connection import DuckDBConnection
from src.database.schema import create_schema
from src.database.ingestion import IngestionPipeline, transform_artportalen_to_db_record
from src.api.unified_client import UnifiedAPIClient
from src.api.gbif_client import GBIFAPIClient
from src.config import Config


class TestUnifiedClientIntegration:
    """Test integration of database with UnifiedAPIClient."""
    
    @pytest.fixture
    def test_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            yield db_path
    
    @pytest.fixture
    def unified_client_with_db(self, test_db_path):
        """Create UnifiedAPIClient with database."""
        # Setup database with test data
        conn = DuckDBConnection(test_db_path)
        create_schema(conn.connection)
        
        # Insert historical test data (2024-01-01, which is >30 days ago if today is later)
        pipeline = IngestionPipeline(conn.connection)
        test_date = date(2024, 1, 15)
        
        record = {
            "occurrenceId": "test-historical",
            "event": {"startDate": test_date.isoformat()},
            "taxon": {
                "scientificName": "Turdus merula",
                "vernacularName": "Koltrast"
            },
            "location": {
                "decimalLatitude": 57.7,
                "decimalLongitude": 11.9
            },
            "occurrence": {"individualCount": 1},
            "identification": {"verified": True}
        }
        
        db_record = transform_artportalen_to_db_record(record)
        if db_record:
            pipeline.ingest_batch([db_record])
        
        # Create unified client
        gbif_client = GBIFAPIClient(Config.GBIF_API_BASE_URL, Config.DATASET_KEY)
        unified = UnifiedAPIClient(
            gbif_client=gbif_client,
            database_path=test_db_path,
            use_database=True
        )
        
        yield unified
    
    def test_database_initialization(self, test_db_path):
        """Test that database is initialized in UnifiedAPIClient."""
        gbif_client = GBIFAPIClient(Config.GBIF_API_BASE_URL, Config.DATASET_KEY)
        unified = UnifiedAPIClient(
            gbif_client=gbif_client,
            database_path=test_db_path,
            use_database=True
        )
        
        # Database should not be available (no schema yet)
        assert unified.database_available is False
        
        # Create schema
        conn = DuckDBConnection(test_db_path)
        create_schema(conn.connection)
        
        # Reinitialize
        unified = UnifiedAPIClient(
            gbif_client=gbif_client,
            database_path=test_db_path,
            use_database=True
        )
        
        assert unified.database_available is True
    
    def test_historical_query_uses_database(self, unified_client_with_db):
        """Test that historical queries use database."""
        # Query for historical date (>30 days ago)
        historical_date = date.today() - timedelta(days=60)
        
        result = unified_client_with_db.search_occurrences(
            start_date=historical_date,
            end_date=historical_date + timedelta(days=1),
            limit=10
        )
        
        # Should use database if available
        if unified_client_with_db.database_available:
            assert result.get("_api_source") in ("database", "mixed")
    
    def test_recent_query_uses_api(self, unified_client_with_db):
        """Test that recent queries use API."""
        # Query for recent date (today)
        recent_date = date.today()
        
        result = unified_client_with_db.search_occurrences(
            start_date=recent_date,
            end_date=recent_date,
            limit=10
        )
        
        # Should use API (gbif or artportalen), not database
        assert result.get("_api_source") in ("gbif", "artportalen", "mixed")
    
    def test_fallback_when_database_unavailable(self):
        """Test fallback to API when database is unavailable."""
        gbif_client = GBIFAPIClient(Config.GBIF_API_BASE_URL, Config.DATASET_KEY)
        unified = UnifiedAPIClient(
            gbif_client=gbif_client,
            use_database=False  # Disable database
        )
        
        # Query should still work, using API
        result = unified.search_occurrences(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            limit=10
        )
        
        assert "results" in result
        assert result.get("_api_source") in ("gbif", "artportalen")
    
    def test_mixed_date_range_query(self, unified_client_with_db):
        """Test mixed date range query (historical + recent)."""
        # Query spanning both historical and recent dates
        historical_start = date.today() - timedelta(days=60)
        recent_end = date.today()
        
        result = unified_client_with_db.search_occurrences(
            start_date=historical_start,
            end_date=recent_end,
            limit=10
        )
        
        # Should handle mixed range
        assert "results" in result
        assert result.get("_api_source") in ("database", "mixed", "gbif", "artportalen")

