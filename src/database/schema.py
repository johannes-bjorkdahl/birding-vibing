"""Database schema definitions and migrations.

Defines the schema for the observations table and provides
schema creation and migration functionality.
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Schema version for migration tracking
SCHEMA_VERSION = 1

# Observations table schema
OBSERVATIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    observation_date DATE NOT NULL,
    species_name TEXT NOT NULL,
    species_scientific TEXT,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    location_name TEXT,
    observer_name TEXT,
    quantity INTEGER,
    verification_status TEXT,
    habitat TEXT,
    coordinate_uncertainty DOUBLE,
    api_source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Index definitions for optimized queries
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_observation_date ON observations(observation_date);",
    "CREATE INDEX IF NOT EXISTS idx_species_name ON observations(species_name);",
    "CREATE INDEX IF NOT EXISTS idx_location ON observations(latitude, longitude);",
    "CREATE INDEX IF NOT EXISTS idx_date_species ON observations(observation_date, species_name);",
    "CREATE INDEX IF NOT EXISTS idx_api_source ON observations(api_source);",
]

# Schema version tracking table
SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def create_schema(connection) -> bool:
    """Create the database schema.
    
    Creates the observations table, indexes, and schema version tracking.
    
    Args:
        connection: DuckDB connection instance
        
    Returns:
        True if schema was created successfully, False otherwise
    """
    try:
        # Create schema version table first
        connection.execute(SCHEMA_VERSION_TABLE)
        logger.info("Schema version table created")
        
        # Create observations table
        connection.execute(OBSERVATIONS_TABLE_SCHEMA)
        logger.info("Observations table created")
        
        # Create indexes
        for index_sql in INDEXES:
            connection.execute(index_sql)
        logger.info(f"Created {len(INDEXES)} indexes")
        
        # Record schema version (use INSERT with ON CONFLICT for DuckDB)
        connection.execute(
            """
            INSERT INTO schema_version (version, applied_at) 
            VALUES (?, ?)
            ON CONFLICT (version) DO UPDATE SET applied_at = ?
            """,
            [SCHEMA_VERSION, datetime.now(), datetime.now()]
        )
        
        connection.commit()
        logger.info(f"Schema created successfully (version {SCHEMA_VERSION})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        return False


def get_schema_version(connection) -> Optional[int]:
    """Get the current schema version.
    
    Args:
        connection: DuckDB connection instance
        
    Returns:
        Schema version number, or None if version table doesn't exist
    """
    try:
        result = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
        if result and result[0] is not None:
            return result[0]
        return None
    except Exception as e:
        logger.debug(f"Could not get schema version: {e}")
        return None


def validate_schema(connection) -> bool:
    """Validate that the schema exists and is correct.
    
    Args:
        connection: DuckDB connection instance
        
    Returns:
        True if schema is valid, False otherwise
    """
    try:
        # Check if observations table exists by trying to query it
        try:
            connection.execute("SELECT COUNT(*) FROM observations LIMIT 1").fetchone()
        except Exception:
            logger.warning("Observations table does not exist")
            return False
        
        # Check schema version
        version = get_schema_version(connection)
        if version is None:
            logger.warning("Schema version table does not exist or is empty")
            return False
        
        if version != SCHEMA_VERSION:
            logger.warning(f"Schema version mismatch: expected {SCHEMA_VERSION}, got {version}")
            return False
        
        logger.info("Schema validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False

