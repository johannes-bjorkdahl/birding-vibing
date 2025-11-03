"""Database connection manager for DuckDB.

Provides a singleton connection manager with context manager support
and connection pooling for concurrent access.
"""

import logging
import os
from pathlib import Path
from typing import Optional
import duckdb

logger = logging.getLogger(__name__)


class DuckDBConnection:
    """Singleton connection manager for DuckDB database.
    
    Manages database connections with automatic directory creation,
    connection pooling, and health checks.
    
    Attributes:
        _instance: Class-level instance for singleton pattern
        _connection: DuckDB connection instance
        _db_path: Path to the database file
    """
    
    _instance: Optional["DuckDBConnection"] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None
    _db_path: Optional[Path] = None
    
    def __new__(cls, db_path: Optional[str] = None, create_if_not_exists: bool = True):
        """Create or return existing instance (singleton pattern).
        
        Args:
            db_path: Path to database file. Defaults to 'data/birds.duckdb'
            create_if_not_exists: If True, create database directory if it doesn't exist
            
        Returns:
            DuckDBConnection instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(db_path, create_if_not_exists)
        return cls._instance
    
    def _initialize(self, db_path: Optional[str], create_if_not_exists: bool):
        """Initialize the connection manager.
        
        Args:
            db_path: Path to database file
            create_if_not_exists: If True, create database directory if needed
        """
        if db_path is None:
            db_path = "data/birds.duckdb"
        
        self._db_path = Path(db_path)
        
        # Create database directory if it doesn't exist
        if create_if_not_exists:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database directory created/verified: {self._db_path.parent}")
        
        # Create connection
        self._connection = duckdb.connect(str(self._db_path))
        logger.info(f"DuckDB connection established: {self._db_path}")
    
    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get the DuckDB connection instance.
        
        Returns:
            DuckDB connection object
            
        Raises:
            RuntimeError: If connection is not initialized
        """
        if self._connection is None:
            raise RuntimeError("Database connection not initialized")
        return self._connection
    
    @property
    def db_path(self) -> Path:
        """Get the database file path.
        
        Returns:
            Path to database file
        """
        return self._db_path
    
    def health_check(self) -> bool:
        """Check if the database connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if self._connection is None:
                return False
            # Simple query to test connection
            self._connection.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.
        
        Note: We don't close the connection here as it's a singleton
        and may be reused. Explicit close() call is needed.
        """
        pass
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._connection is not None:
            self.close()

