"""Database module for DuckDB integration.

This module provides database functionality for storing and querying
bird observation data using DuckDB as the local database layer.
"""

from src.database.connection import DuckDBConnection
from src.database.queries import DatabaseQueryClient
from src.database.schema import create_schema, get_schema_version, validate_schema
from src.database.ingestion import IngestionPipeline, transform_artportalen_to_db_record

__all__ = [
    "DuckDBConnection",
    "DatabaseQueryClient",
    "create_schema",
    "get_schema_version",
    "validate_schema",
    "IngestionPipeline",
    "transform_artportalen_to_db_record",
]

