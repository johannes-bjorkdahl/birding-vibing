# Data Ingestion Guide

This guide explains how to load historical bird observation data into the DuckDB database.

## Overview

The data ingestion process fetches observations from the Artportalen API and stores them in DuckDB. The system handles API rate limits, pagination, and large datasets automatically.

## API Constraints

### Artportalen API Limits

- **Page Size**: Maximum 1000 records per request
- **Total Records**: Maximum 10,000 records per query
- **Rate Limiting**: Recommended 1 second delay between requests

### Handling Large Datasets

The ingestion system automatically handles API limits by:

1. **Chunk Detection**: Tests if a date range exceeds 10,000 records
2. **Automatic Splitting**: Splits large months into weekly chunks
3. **Pagination**: Uses pagination to fetch all records (up to 10,000 per chunk)
4. **Rate Limiting**: Implements delays between API requests

## Loading Historical Data

### Basic Usage

```bash
# Load a specific year range
uv run python scripts/load_historical_data.py --start-year 2020 --end-year 2024

# Load specific months
uv run python scripts/load_historical_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 6

# Dry run (test without saving)
uv run python scripts/load_historical_data.py --start-year 2020 --end-year 2021 --dry-run
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--start-year` | Start year (2005-2025) | Required |
| `--end-year` | End year (2005-2025) | Required |
| `--start-month` | Start month (1-12) | 1 |
| `--end-month` | End month (1-12) | 12 |
| `--db-path` | Database file path | `data/birds.duckdb` |
| `--batch-size` | Batch size for ingestion | 1000 |
| `--rate-limit-delay` | Delay between requests (seconds) | 1.0 |
| `--no-skip-existing` | Re-fetch existing data | False (skip existing) |
| `--dry-run` | Test without saving | False |
| `--max-records` | Maximum records to fetch (testing) | None (all) |

### Example: Loading 5 Years

```bash
# Load 2020-2024 (recommended for testing)
uv run python scripts/load_historical_data.py \
    --start-year 2020 \
    --end-year 2024 \
    --batch-size 1000 \
    --rate-limit-delay 1.0
```

**Estimated Time**: ~2-4 hours (depends on data volume)

**Estimated Records**: ~500,000 - 1,000,000 records

### Example: Loading Full Dataset (20 Years)

```bash
# Load 2005-2025 (full dataset)
uv run python scripts/load_historical_data.py \
    --start-year 2005 \
    --end-year 2025 \
    --batch-size 1000 \
    --rate-limit-delay 1.0
```

**Estimated Time**: ~8-16 hours (depends on data volume and API performance)

**Estimated Records**: ~2,000,000 - 5,000,000 records

**Warning**: This will make thousands of API requests. Ensure you have:
- Stable internet connection
- Sufficient disk space (2-5 GB)
- API key configured
- Time to monitor progress

## Ingestion Process

### Step-by-Step Process

1. **Initialization**
   - Connect to database
   - Create schema if needed
   - Authenticate with Artportalen API

2. **Date Chunking**
   - Split date range into monthly chunks
   - For large months (>10,000 records), split into weekly chunks
   - Generate list of date ranges to process

3. **Data Fetching**
   - For each date chunk:
     - Check if data already exists (unless `--no-skip-existing`)
     - Fetch data from API with pagination
     - Handle API rate limits
     - Transform API responses to database format

4. **Data Ingestion**
   - Batch insert records using upsert (`ON CONFLICT DO UPDATE`)
   - Handle duplicates automatically
   - Track progress and log errors

5. **Completion**
   - Validate ingested data
   - Report statistics
   - Log completion status

### Chunk Splitting Strategy

When a month exceeds 10,000 records:

1. **Detection**: Test API call to check total count
2. **Split**: Divide month into weekly chunks
3. **Process**: Fetch each week separately
4. **Log**: Warn about chunk splitting in logs

Example:
- January 2020: 15,000 records
- Split into: Week 1 (Jan 1-7), Week 2 (Jan 8-14), etc.
- Fetch each week separately

### Pagination Handling

For chunks with >1000 records:

1. **Initial Request**: Fetch first 1000 records
2. **Check Total**: API returns total count
3. **Calculate Pages**: `ceil(total / 1000)` pages needed
4. **Fetch Remaining**: Request subsequent pages with offset
5. **Limit**: Stop at 10,000 records per chunk (API limit)

## Data Transformation

### API Response → Database Record

The `transform_artportalen_to_db_record()` function maps API fields:

```python
{
    "occurrenceId": "12345",
    "event": {"startDate": "2020-01-15T10:00:00+01:00"},
    "taxon": {
        "vernacularName": "Koltrast",
        "scientificName": "Turdus merula"
    },
    "location": {
        "decimalLatitude": 57.7,
        "decimalLongitude": 11.9,
        "locality": "Göteborg"
    },
    ...
}
```

Transforms to:

```python
{
    "id": "12345",
    "observation_date": date(2020, 1, 15),
    "species_name": "Koltrast",
    "species_scientific": "Turdus merula",
    "latitude": 57.7,
    "longitude": 11.9,
    "location_name": "Göteborg",
    ...
}
```

### Field Mapping

See [Database Schema Documentation](DATABASE_SCHEMA.md#data-transformation) for detailed mapping.

## Error Handling

### API Errors

- **Rate Limiting**: Automatic retry with exponential backoff
- **Timeout**: Retry with increased timeout
- **Invalid Response**: Log error and skip record
- **API Limit**: Split into smaller chunks

### Database Errors

- **Lock Errors**: Wait and retry
- **Constraint Violations**: Handle duplicates with upsert
- **Schema Errors**: Auto-create schema if missing

### Recovery

If ingestion fails:

1. **Resume**: Run again with same parameters (skips existing data)
2. **Partial Data**: Check logs for failed chunks
3. **Re-fetch**: Use `--no-skip-existing` to re-fetch specific ranges

## Monitoring Progress

### Log Files

Ingestion logs are saved to:
- `data_ingestion.log` - Detailed ingestion log
- Console output - Progress updates

### Progress Indicators

The script provides:
- Chunk progress: `[5/24 (20.8%)] Processing 2020-01`
- Record counts: `Fetched 1234 records`
- Time estimates: `Estimated remaining: 2 hours`

### Validation

After ingestion, validate data:

```bash
uv run python scripts/validate_data.py
```

## Performance Optimization

### Batch Size

- **Default**: 1000 records per batch
- **Larger**: Faster ingestion, more memory usage
- **Smaller**: Slower ingestion, less memory usage

### Rate Limiting

- **Default**: 1.0 second delay between requests
- **Faster**: Risk of rate limiting
- **Slower**: More conservative, safer

### Parallel Processing

Currently single-threaded. Future enhancement:
- Parallel chunk processing
- Concurrent API requests (with rate limiting)
- Batch processing optimization

## Best Practices

### Recommended Approach

1. **Start Small**: Test with 1-2 years first
2. **Validate**: Run validation after each load
3. **Monitor**: Watch logs for errors
4. **Incremental**: Load in phases (e.g., 5 years at a time)
5. **Backup**: Backup database before large loads

### Loading Strategy

For 20 years of data:

```bash
# Phase 1: Test with recent data
uv run python scripts/load_historical_data.py --start-year 2020 --end-year 2025

# Phase 2: Load middle period
uv run python scripts/load_historical_data.py --start-year 2015 --end-year 2019

# Phase 3: Load early period
uv run python scripts/load_historical_data.py --start-year 2005 --end-year 2014
```

### Maintenance

- **Regular Updates**: Use `update_database.py` for recent data
- **Validation**: Run validation weekly
- **Monitoring**: Check database size and performance
- **Cleanup**: Remove old backups periodically

## Troubleshooting

### Common Issues

1. **API Rate Limiting**
   - Increase `--rate-limit-delay` to 2.0 seconds
   - Reduce batch size
   - Split into smaller date ranges

2. **Database Locked**
   - Stop Streamlit app
   - Wait for locks to release
   - Check for other processes

3. **Out of Memory**
   - Reduce batch size
   - Process smaller date ranges
   - Check system resources

4. **Missing Data**
   - Check API availability
   - Verify API key is valid
   - Check date ranges are valid
   - Review logs for errors

### Getting Help

- Check logs: `data_ingestion.log`
- Validate data: `scripts/validate_data.py`
- Review API docs: [API Troubleshooting Guide](API_TROUBLESHOOTING.md)

## Related Documentation

- [Database Setup Guide](DATABASE_SETUP.md)
- [Database Schema Documentation](DATABASE_SCHEMA.md)
- [API Troubleshooting Guide](API_TROUBLESHOOTING.md)

