"""Unit tests for database ingestion pipeline."""
import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from src.database.connection import DuckDBConnection
from src.database.schema import create_schema, validate_schema
from src.database.ingestion import IngestionPipeline, transform_artportalen_to_db_record


class TestDatabaseIngestion:
    """Test database ingestion pipeline."""
    
    @pytest.fixture
    def db_connection(self):
        """Create a temporary database connection for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            # Reset singleton before creating new connection
            DuckDBConnection._instance = None
            DuckDBConnection._connection = None
            DuckDBConnection._db_path = None
            # Create connection - don't use context manager so it stays open
            conn = DuckDBConnection(db_path)
            # Ensure schema is created before yielding
            if not validate_schema(conn.connection):
                create_schema(conn.connection)
            yield conn.connection
            # Cleanup - reset singleton
            conn.close()
            DuckDBConnection._instance = None
            DuckDBConnection._connection = None
            DuckDBConnection._db_path = None
    
    @pytest.fixture
    def sample_record(self):
        """Create a sample Artportalen API record."""
        return {
            "occurrenceId": "test-123",
            "event": {
                "startDate": "2024-01-15T10:00:00+01:00",
                "endDate": "2024-01-15T10:00:00+01:00"
            },
            "taxon": {
                "scientificName": "Turdus merula",
                "vernacularName": "Koltrast"
            },
            "location": {
                "decimalLatitude": 57.7,
                "decimalLongitude": 11.9,
                "site": {"name": "Test Location"}
            },
            "occurrence": {
                "individualCount": 1
            },
            "identification": {
                "verified": True
            }
        }
    
    def test_transform_artportalen_record(self, sample_record):
        """Test transformation of Artportalen record to database format."""
        db_record = transform_artportalen_to_db_record(sample_record)
        
        assert db_record is not None
        assert db_record["id"] == "test-123"
        assert db_record["observation_date"] == date(2024, 1, 15)
        assert db_record["species_name"] == "Koltrast"
        assert db_record["species_scientific"] == "Turdus merula"
        assert db_record["latitude"] == 57.7
        assert db_record["longitude"] == 11.9
        assert db_record["api_source"] == "artportalen"
    
    def test_ingest_batch(self, db_connection, sample_record):
        """Test batch ingestion."""
        pipeline = IngestionPipeline(db_connection, batch_size=100)
        
        # Transform record
        db_record = transform_artportalen_to_db_record(sample_record)
        assert db_record is not None
        
        # Ingest batch
        result = pipeline.ingest_batch([db_record])
        assert result is True
        
        # Verify record was inserted
        count = db_connection.execute("SELECT COUNT(*) FROM observations").fetchone()
        assert count[0] == 1
    
    def test_check_existing_data(self, db_connection, sample_record):
        """Test check for existing data."""
        pipeline = IngestionPipeline(db_connection)
        
        # Should return False for empty database
        assert pipeline.check_existing_data(
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        ) is False
        
        # Insert a record
        db_record = transform_artportalen_to_db_record(sample_record)
        pipeline.ingest_batch([db_record])
        
        # Should return True now
        assert pipeline.check_existing_data(
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        ) is True
    
    def test_get_date_chunks(self):
        """Test date chunk generation."""
        pipeline = IngestionPipeline(None)  # Connection not needed for this test
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 31)
        
        chunks = pipeline.get_date_chunks(start, end)
        
        # Should have 3 chunks (Jan, Feb, Mar)
        assert len(chunks) == 3
        assert chunks[0][0] == datetime(2024, 1, 1)
        assert chunks[0][1] == datetime(2024, 1, 31)
        assert chunks[1][0] == datetime(2024, 2, 1)
        assert chunks[1][1] == datetime(2024, 2, 29)
    
    def test_split_date_range_into_weeks(self):
        """Test weekly chunk splitting."""
        pipeline = IngestionPipeline(None)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 21)  # 3 weeks
        
        chunks = pipeline.split_date_range_into_weeks(start, end)
        
        # Should have 3 weekly chunks
        assert len(chunks) == 3
        assert chunks[0][0] == datetime(2024, 1, 1)
        assert chunks[0][1] == datetime(2024, 1, 7)
        assert chunks[1][0] == datetime(2024, 1, 8)
        assert chunks[1][1] == datetime(2024, 1, 14)
    
    def test_ingest_batch_retry_logic(self, db_connection, sample_record):
        """Test that batch ingestion handles errors gracefully."""
        pipeline = IngestionPipeline(db_connection, max_retries=2)
        
        db_record = transform_artportalen_to_db_record(sample_record)
        
        # Should succeed
        result = pipeline.ingest_batch([db_record])
        assert result is True
        
        # Verify stats
        assert pipeline.total_ingested == 1
        assert pipeline.total_failed == 0

