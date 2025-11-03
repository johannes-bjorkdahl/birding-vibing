# Database Setup Guide

This guide explains how to set up and configure the DuckDB local database for the Birding Vibing application.

## Overview

The application uses DuckDB as a local database layer to store historical bird observation data (2005-2025). This enables fast analytical queries while maintaining full backward compatibility with API-based functionality.

## Architecture

- **DuckDB**: Local database for historical data storage
- **Artportalen API**: Real-time data source (last 30 days)
- **GBIF API**: Fallback and redundancy data source
- **Smart Query Routing**: Automatically selects between DuckDB, Artportalen API, and GBIF API based on date ranges

## Configuration

### Environment Variables

The database can be configured via environment variables or `.streamlit/secrets.toml`:

```toml
[ database]
database_path = "data/birds.duckdb"
database_date_threshold_days = 30
use_database = true
```

### Configuration Options

- `database_path`: Path to the DuckDB database file (default: `data/birds.duckdb`)
- `database_date_threshold_days`: Days threshold for using database vs API (default: 30)
- `use_database`: Feature flag to enable/disable database (default: `true`)

## Initial Setup

### 1. Install Dependencies

The database functionality requires DuckDB, which is included in `pyproject.toml`:

```bash
uv sync
```

### 2. Create Database Directory

The database directory is created automatically on first use, but you can create it manually:

```bash
mkdir -p data
```

### 3. Initialize Database Schema

The schema is created automatically when the application starts. To manually initialize:

```python
from src.database import DuckDBConnection, create_schema
from src.config import Config

with DuckDBConnection(Config.DATABASE_PATH) as db:
    create_schema(db.connection)
```

### 4. Load Historical Data

Use the `load_historical_data.py` script to populate the database:

```bash
# Load a specific year range (recommended for testing)
uv run python scripts/load_historical_data.py --start-year 2020 --end-year 2024

# Load last 5 years
uv run python scripts/load_historical_data.py --start-year 2020 --end-year 2025

# Full 20 years (2005-2025) - takes many hours
uv run python scripts/load_historical_data.py --start-year 2005 --end-year 2025
```

**Note**: Loading 20 years of data will take many hours and make thousands of API requests. Start with a smaller range for testing.

### 5. Verify Database

Validate the database after loading:

```bash
uv run python scripts/validate_data.py
```

## Database Location

By default, the database is stored at:
- `data/birds.duckdb` - Main database file
- `data/birds.duckdb.wal` - Write-ahead log (created automatically)

## Updating the Database

### Daily Updates

Use the `update_database.py` script to keep the database current:

```bash
# Update with last 30 days of data (default)
uv run python scripts/update_database.py

# Update with custom number of days
uv run python scripts/update_database.py --days 60

# Dry run (test without saving)
uv run python scripts/update_database.py --dry-run
```

### Automation

You can schedule daily updates using cron (Linux/Mac):

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/birding-vibing && uv run python scripts/update_database.py >> update.log 2>&1
```

## Troubleshooting

### Database Lock Errors

If you see "Conflicting lock is held" errors:

1. **Stop the Streamlit app** - The database cannot be accessed while Streamlit is running
2. **Check for other processes** - Ensure no other scripts are using the database
3. **Wait a few seconds** - Sometimes locks take a moment to release

### Database Not Found

If the database file doesn't exist:

1. The schema will be created automatically on first use
2. Or manually create it using the initialization steps above

### Schema Validation Failures

If schema validation fails:

1. Check the schema version: `uv run python scripts/validate_data.py`
2. The schema will be automatically recreated if invalid
3. If issues persist, you may need to delete the database and recreate it

### API Rate Limits

The Artportalen API has limits:
- 1000 records per page
- 10,000 total records per query

The ingestion script automatically handles these limits by:
- Splitting large date ranges into smaller chunks
- Using pagination to fetch all records
- Implementing rate limiting between requests

## Backup and Recovery

### Backup

To backup the database:

```bash
cp data/birds.duckdb data/birds.duckdb.backup
```

### Restore

To restore from backup:

```bash
cp data/birds.duckdb.backup data/birds.duckdb
```

### Recovery

If the database becomes corrupted:

1. Delete the database file: `rm data/birds.duckdb`
2. Reinitialize the schema (automatic on next app start)
3. Reload data using `load_historical_data.py`

## Performance Considerations

- **Storage**: 20 years of data will use approximately 1-2 GB of disk space
- **Query Speed**: Database queries are typically 10-100x faster than API calls
- **Memory**: DuckDB is optimized for analytical queries and uses minimal memory

## Disabling the Database

To disable database functionality (use APIs only):

1. Set `use_database = false` in configuration
2. Or set `USE_DATABASE=false` environment variable
3. The application will automatically fall back to API-only mode

## Next Steps

- See [Database Schema Documentation](DATABASE_SCHEMA.md) for schema details
- See [Data Ingestion Guide](DATA_INGESTION.md) for loading data
- See [API Troubleshooting Guide](../docs/API_TROUBLESHOOTING.md) for API issues

