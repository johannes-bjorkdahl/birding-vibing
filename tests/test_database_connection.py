"""Unit tests for database connection manager."""
import pytest
import tempfile
import os
from pathlib import Path
from src.database.connection import DuckDBConnection


class TestDuckDBConnection:
    """Test DuckDBConnection class."""
    
    def test_connection_creation(self):
        """Test that connection can be created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            conn = DuckDBConnection(db_path)
            assert conn.connection is not None
            assert conn.db_path == Path(db_path)
    
    def test_singleton_pattern(self):
        """Test that singleton pattern works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            conn1 = DuckDBConnection(db_path)
            conn2 = DuckDBConnection(db_path)
            assert conn1 is conn2
    
    def test_health_check(self):
        """Test health check functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            conn = DuckDBConnection(db_path)
            assert conn.health_check() is True
    
    def test_context_manager(self):
        """Test context manager support."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            with DuckDBConnection(db_path) as conn:
                assert conn.connection is not None
                assert conn.health_check() is True
    
    def test_automatic_directory_creation(self):
        """Test that database directory is created automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "test.duckdb")
            # Reset singleton before creating new connection
            DuckDBConnection._instance = None
            DuckDBConnection._connection = None
            DuckDBConnection._db_path = None
            # DuckDBConnection should create the directory
            conn = DuckDBConnection(db_path)
            # Directory should exist after connection is established
            assert os.path.exists(os.path.dirname(db_path))
            assert conn.db_path == Path(db_path)
            # Verify database file is created
            assert os.path.exists(db_path) or os.path.exists(db_path.replace(".duckdb", ".duckdb.wal"))
            # Cleanup
            conn.close()
            DuckDBConnection._instance = None
            DuckDBConnection._connection = None
            DuckDBConnection._db_path = None

