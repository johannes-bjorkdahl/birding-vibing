# Test Suite for Birding Vibing

This directory contains tests for the filtering functionality of the Birding Vibing application.

## Test Structure

- `test_api_client.py` - Tests for the GBIF API client filtering logic
  - Date range filtering
  - Location filtering (state/province and locality)
  - Combined filters
  - Error handling

- `test_filters.py` - Tests for filter parameter generation and validation
  - Date filter defaults
  - Parameter formatting
  - Edge cases

- `test_integration.py` - Integration tests for the complete filter workflow
  - End-to-end filter combinations
  - Default date range integration

## Running Tests

### Install Test Dependencies

```bash
uv sync --extra dev
```

### Run All Tests

```bash
uv run pytest
```

Or use the convenience script:

```bash
./run_tests.sh
```

### Run Specific Test File

```bash
uv run pytest tests/test_api_client.py
```

### Run with Coverage

```bash
uv run pytest --cov=src --cov-report=html
```

### Run with Verbose Output

```bash
uv run pytest -v
```

## Test Coverage

The tests verify:

1. **Date Range Filtering**
   - Correct formatting of date ranges for GBIF API (`eventDate` parameter)
   - Default date range (yesterday and today)
   - Single date filtering
   - Date ranges crossing month/year boundaries

2. **Location Filtering**
   - State/province filtering
   - Locality (city/town) filtering
   - Combined location filters
   - Empty/None location handling

3. **Filter Combinations**
   - Date + location filters together
   - All filters enabled
   - Minimal filter sets

4. **Error Handling**
   - API error responses
   - Missing response fields
   - Invalid date ranges

## Notes

- Tests use mocking to avoid actual API calls
- All date comparisons use `date` objects (not datetime)
- Tests verify the exact format expected by GBIF API

