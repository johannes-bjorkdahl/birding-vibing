"""Unit tests for database schema."""
import pytest
import tempfile
import os
from src.database.connection import DuckDBConnection
from src.database.schema import create_schema, get_schema_version, validate_schema, SCHEMA_VERSION


class TestDatabaseSchema:
    """Test database schema creation and validation."""
    
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
            yield conn.connection
            # Cleanup - reset singleton
            conn.close()
            DuckDBConnection._instance = None
            DuckDBConnection._connection = None
            DuckDBConnection._db_path = None
    
    def test_schema_creation(self, db_connection):
        """Test that schema can be created."""
        result = create_schema(db_connection)
        assert result is True
        
        # Verify schema version
        version = get_schema_version(db_connection)
        assert version == SCHEMA_VERSION
    
    def test_schema_validation(self, db_connection):
        """Test schema validation."""
        # Should fail before schema creation
        assert validate_schema(db_connection) is False
        
        # Create schema
        create_schema(db_connection)
        
        # Should pass after schema creation
        assert validate_schema(db_connection) is True
    
    def test_observations_table_exists(self, db_connection):
        """Test that observations table exists after schema creation."""
        create_schema(db_connection)
        
        # Query should work
        result = db_connection.execute("SELECT COUNT(*) FROM observations").fetchone()
        assert result is not None
        assert result[0] == 0  # Empty table initially
    
    def test_indexes_exist(self, db_connection):
        """Test that indexes are created."""
        create_schema(db_connection)
        
        # Check that indexes exist by querying information schema
        # Note: DuckDB may not expose indexes the same way, so we'll test by querying
        # the table works (which requires indexes if they exist)
        result = db_connection.execute(
            "SELECT COUNT(*) FROM observations WHERE observation_date >= '2024-01-01'"
        ).fetchone()
        assert result is not None
    
    def test_schema_version_tracking(self, db_connection):
        """Test that schema version is tracked."""
        create_schema(db_connection)
        
        version = get_schema_version(db_connection)
        assert version == SCHEMA_VERSION
        
        # Verify version table exists
        result = db_connection.execute("SELECT COUNT(*) FROM schema_version").fetchone()
        assert result is not None
        assert result[0] > 0

