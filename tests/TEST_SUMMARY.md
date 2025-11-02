# Filter Tests Summary

## Overview

This test suite verifies that the new filtering functionality (date range and location filtering) works correctly. The tests cover:

1. **Date Range Filtering** - Verifies that date ranges are correctly formatted and sent to the GBIF API
2. **Location Filtering** - Tests state/province and locality filtering
3. **Filter Combinations** - Ensures multiple filters work together
4. **Edge Cases** - Handles various edge cases and error conditions

## Test Files

### `test_api_client.py`
Tests the core API client filtering logic:
- **TestDateRangeFiltering**: 6 tests
  - Date range formatting (`eventDate` parameter)
  - Single date filtering
  - Default date range (yesterday and today)
  - Multiple day ranges
  - Month boundary crossing
  
- **TestLocationFiltering**: 4 tests
  - State/province filtering
  - Locality filtering
  - Combined location filters
  - None/empty handling

- **TestCombinedFilters**: 3 tests
  - Date + location filters together
  - Response structure handling
  - Error handling

**Total: 13 tests**

### `test_filters.py`
Tests filter parameter generation and validation:
- **TestDateFilterDefaults**: 2 tests
- **TestFilterParameters**: 2 tests
- **TestFilterCombinations**: 4 tests
- **TestDateEdgeCases**: 3 tests
- **TestLocationEdgeCases**: 3 tests

**Total: 14 tests**

### `test_integration.py`
Integration tests for complete filter workflow:
- **TestFilterIntegration**: 3 tests
  - Search with date range
  - Date and location filter combination
  - Default date range integration

**Total: 3 tests**

## Key Test Scenarios

### ✅ Date Range Filtering
- Verifies `eventDate` parameter format: `YYYY-MM-DD,YYYY-MM-DD`
- Tests default range (yesterday to today)
- Handles single dates, multi-day ranges, and month/year boundaries

### ✅ Location Filtering
- State/province parameter (`stateProvince`)
- Locality parameter (`locality`)
- Combined location filters
- Empty/None value handling

### ✅ Error Handling
- HTTP errors
- Missing response fields
- Invalid date ranges

### ✅ Edge Cases
- Same start/end date
- Year boundary crossing
- Whitespace-only location strings
- Special characters in location names

## Running the Tests

```bash
# Install test dependencies
uv sync --extra dev

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api_client.py

# Run with verbose output
pytest -v
```

## Expected Results

All tests should pass, verifying that:
1. Date ranges are correctly formatted for GBIF API
2. Location filters are properly included in API requests
3. Combined filters work together correctly
4. Edge cases are handled gracefully
5. Error conditions are properly managed

## Test Coverage

The tests use mocking to avoid actual API calls, focusing on:
- Parameter formatting and validation
- API request construction
- Response handling
- Error scenarios

## Notes

- Tests mock `httpx.Client` to avoid making real API calls
- All date comparisons use `date` objects (not `datetime`)
- Tests verify exact GBIF API parameter formats
- Swedish characters in location names are tested


