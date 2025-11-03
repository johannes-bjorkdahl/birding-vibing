"""Unit tests for database query interface."""
import pytest
import tempfile
import os
from datetime import date
from src.database.connection import DuckDBConnection
from src.database.schema import create_schema, validate_schema
from src.database.ingestion import IngestionPipeline, transform_artportalen_to_db_record
from src.database.queries import DatabaseQueryClient


class TestDatabaseQueries:
    """Test database query interface."""
    
    @pytest.fixture
    def db_connection(self):
        """Create a temporary database connection with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            # Create connection - don't use context manager so it stays open
            conn = DuckDBConnection(db_path)
            # Ensure schema is created
            from src.database.schema import validate_schema
            if not validate_schema(conn.connection):
                create_schema(conn.connection)
            
            # Insert test data
            pipeline = IngestionPipeline(conn.connection)
            records = [
                {
                    "occurrenceId": f"test-{i}",
                    "event": {"startDate": f"2024-01-{15+i:02d}T10:00:00+01:00"},
                    "taxon": {
                        "scientificName": "Turdus merula",
                        "vernacularName": "Koltrast"
                    },
                    "location": {
                        "decimalLatitude": 57.7 + (i * 0.01),
                        "decimalLongitude": 11.9 + (i * 0.01),
                        "site": {"name": f"Location {i}"}
                    },
                    "occurrence": {"individualCount": 1},
                    "identification": {"verified": True}
                }
                for i in range(5)
            ]
            
            db_records = [transform_artportalen_to_db_record(r) for r in records]
            pipeline.ingest_batch([r for r in db_records if r])
            
            yield conn.connection
            # Cleanup - reset singleton
            conn.close()
            DuckDBConnection._instance = None
            DuckDBConnection._connection = None
            DuckDBConnection._db_path = None
    
    def test_search_occurrences_basic(self, db_connection):
        """Test basic search functionality."""
        client = DatabaseQueryClient(db_connection)
        
        result = client.search_occurrences(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            limit=10
        )
        
        assert "results" in result
        assert "count" in result
        assert result["_api_source"] == "database"
        assert len(result["results"]) <= 10
    
    def test_search_occurrences_date_filter(self, db_connection):
        """Test date filtering."""
        client = DatabaseQueryClient(db_connection)
        
        # Query for specific date range
        result = client.search_occurrences(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 20),
            limit=10
        )
        
        assert result["count"] > 0
        
        # Verify all results are in date range
        for record in result["results"]:
            event_date = record.get("eventDate")
            if event_date:
                record_date = date.fromisoformat(event_date)
                assert date(2024, 1, 15) <= record_date <= date(2024, 1, 20)
    
    def test_search_occurrences_pagination(self, db_connection):
        """Test pagination."""
        client = DatabaseQueryClient(db_connection)
        
        # Get first page
        result1 = client.search_occurrences(limit=2, offset=0)
        assert len(result1["results"]) <= 2
        
        # Get second page
        result2 = client.search_occurrences(limit=2, offset=2)
        assert len(result2["results"]) <= 2
        
        # Results should be different
        if result1["results"] and result2["results"]:
            assert result1["results"][0]["id"] != result2["results"][0]["id"]
    
    def test_search_occurrences_location_filter(self, db_connection):
        """Test location filtering."""
        client = DatabaseQueryClient(db_connection)
        
        # Filter by state/province (location_name)
        result = client.search_occurrences(
            state_province="Location",
            limit=10
        )
        
        assert "results" in result
        assert result["_api_source"] == "database"
    
    def test_search_occurrences_response_format(self, db_connection):
        """Test that response format matches API format."""
        client = DatabaseQueryClient(db_connection)
        
        result = client.search_occurrences(limit=1)
        
        if result["results"]:
            record = result["results"][0]
            
            # Check for normalized fields
            assert "eventDate" in record or "year" in record
            assert "scientificName" in record or "species" in record
            assert "decimalLatitude" in record or "latitude" in record
            assert "decimalLongitude" in record or "longitude" in record
            assert "_api_source" in record
            assert record["_api_source"] == "database"
    
    def test_search_occurrences_empty_result(self, db_connection):
        """Test query with no results."""
        client = DatabaseQueryClient(db_connection)
        
        result = client.search_occurrences(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 31),
            limit=10
        )
        
        assert result["results"] == []
        assert result["count"] == 0
        assert result["_api_source"] == "database"

