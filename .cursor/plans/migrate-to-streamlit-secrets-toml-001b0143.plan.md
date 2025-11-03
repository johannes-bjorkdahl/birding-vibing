<!-- 001b0143-e89f-4cc3-837c-866876e810db 97ecd825-4434-406e-854d-e278fbdbff54 -->
# DuckDB Historical Data Integration Plan

## Overview

Integrate DuckDB as local database layer for 20 years of Artportalen bird observation data (2005-2025), enabling fast analytical queries for migration patterns and hotspot visualizations while maintaining full backward compatibility with existing API-based functionality.

## Architecture Strategy

**Three-Layer Data Access:**

1. **DuckDB (Local Database)** - Primary data source for historical queries (2005-2025)
2. **Artportalen API** - Real-time data updates (last 30 days)
3. **GBIF API** - Fallback and redundancy

**Smart Query Routing:**

- Historical queries (older than 30 days) → DuckDB
- Recent queries (last 30 days) → Artportalen API
- Fallback chain: DuckDB → Artportalen → GBIF

## API Constraints & Limitations

**Artportalen API Limits (per official documentation):**

- **Maximum page size:** 1000 records per page
- **Maximum total per search query:** 10,000 records (skip + take cannot exceed 10,000)
- **Source:** https://github.com/biodiversitydata-se/SOS/blob/master/Docs/FAQ.md

**Implications for Data Ingestion:**

1. **Monthly chunks may exceed limits:** Some months (especially migration seasons) may have >10,000 observations
2. **Strategies for handling large datasets:**

   - **Option A:** Break large months into smaller chunks (weekly/bi-weekly)
   - **Option B:** Use export endpoints for date ranges >10,000 records:
     - `/Exports/Order/Csv` - Up to 2 million observations (asynchronous, email delivery)
     - `/Exports/Order/GeoJson` - Up to 2 million observations
     - `/Exports/Order/DwC` - Up to 2 million observations
   - **Option C:** Use aggregation endpoints for summary data if detailed records not needed

**Export Endpoints (for large datasets):**

- Download endpoints: 25,000 observations limit (synchronous)
- Order endpoints: Up to 2 million observations (asynchronous, email delivery)
- Available formats: Csv, GeoJson, Excel, DwC-A

## Phase 1: Foundation & Setup (Week 1)

### Step 1.1: Add DuckDB Dependency

- Add `duckdb>=1.0.0` to `pyproject.toml` dependencies
- Run `uv sync` to install
- Verify import works: `import duckdb`

**Files to modify:**

- `pyproject.toml`

**Validation:**

- Check import succeeds
- Verify DuckDB version >= 1.0.0

### Step 1.2: Create Database Module Structure

- Create `src/database/` directory
- Create `src/database/__init__.py`
- Create `src/database/connection.py` - Database connection manager
- Create `src/database/schema.py` - Schema definitions and migrations
- Create `src/database/ingestion.py` - Data ingestion pipeline
- Create `src/database/queries.py` - Query helpers

**Files to create:**

- `src/database/__init__.py`
- `src/database/connection.py`
- `src/database/schema.py`
- `src/database/ingestion.py`
- `src/database/queries.py`

**Validation:**

- Verify all modules import successfully
- Check directory structure matches plan

### Step 1.3: Database Connection Manager

- Implement `DuckDBConnection` class in `connection.py`
- Handle database file path configuration (default: `data/birds.duckdb`)
- Support initialization flag (create if not exists)
- Add connection pooling for concurrent access
- Add context manager support (`with` statement)

**Key features:**

- Singleton pattern for connection reuse
- Automatic database directory creation
- Connection health checks

**Files to create:**

- `src/database/connection.py`

**Validation:**

- Test connection creation
- Test context manager usage
- Verify connection reuse works

### Step 1.4: Database Schema Design

- Define schema in `schema.py` for `observations` table
- Fields: id, observation_date, species_name, species_scientific, latitude, longitude, location_name, observer_name, quantity, verification_status, habitat, coordinate_uncertainty, api_source, created_at, updated_at
- Add indexes: date, species, location (lat/lon), date+species
- Create migration system (version tracking)
- Add schema validation functions

**Schema considerations:**

- Optimize for analytical queries (date range, species, location)
- Support both Artportalen and GBIF data formats
- Include metadata for tracking data provenance

**Files to create:**

- `src/database/schema.py`

**Validation:**

- Test schema creation
- Verify indexes are created correctly
- Test migration system

## Phase 2: Data Ingestion Pipeline (Week 1-2)

### Step 2.1: Ingestion Framework

- Create `IngestionPipeline` class in `ingestion.py`
- Implement batch processing (chunks of dates)
- Add progress tracking and logging
- Add error handling and retry logic
- Support incremental updates (check existing data)
- Handle API limits (10,000 records per search query)

**Key features:**

- Process data in monthly chunks (2005-2025 = 240 months)
- Auto-detect months exceeding 10,000 records and split into smaller chunks (weekly/bi-weekly)
- Rate limiting to respect API limits
- Resume capability (skip already-ingested months)
- Transaction support (rollback on errors)
- Warning logs when API limits are reached

**API Limit Handling:**

- Check total count from first response
- If >10,000 records: automatically split month into smaller chunks
- Log warnings when limits are encountered
- Consider future enhancement: use export endpoints for very large ranges

**Files to create:**

- `src/database/ingestion.py`

**Validation:**

- Test with small date range (1 month)
- Verify error handling works
- Test resume functionality

### Step 2.2: Artportalen Data Adapter

- Create adapter function to transform Artportalen API responses to database schema
- Handle field mapping and data type conversion
- Validate required fields before insertion
- Handle missing/null values gracefully

**Files to modify:**

- `src/database/ingestion.py`

**Validation:**

- Test with real Artportalen API response
- Verify all fields map correctly
- Test edge cases (missing data, nulls)

### Step 2.3: Historical Data Loading Script

- Create `scripts/load_historical_data.py` script
- Implement date range processing (2005-2025)
- Add progress reporting (CLI progress bar)
- Add configuration for date ranges, batch sizes
- Add dry-run mode for testing
- Handle API limits automatically

**Script features:**

- Command-line interface with argparse
- Progress bars (tqdm or similar)
- Logging to file
- Resume support
- `--max-records` parameter for testing (limits records per month)
- Automatic chunk splitting when months exceed 10,000 records

**API Limit Awareness:**

- Script respects 10,000 record limit per search query
- Automatically splits large months into smaller chunks
- Logs warnings when limits are encountered
- Provides guidance on using export endpoints for very large datasets

**Files to create:**

- `scripts/load_historical_data.py`

**Validation:**

- Test with small date range first (1 year)
- Verify data loads correctly
- Test resume functionality

### Step 2.4: Initial Data Load (Test)

- Load 1 year of test data (2024 only)
- Verify data integrity (counts, date ranges)
- Test query performance
- Measure load time and storage size
- Test API limit handling (months with >10,000 records)

**Validation:**

- Verify record counts match API responses
- Check date ranges are correct
- Test basic queries work
- Document storage size and load time
- Verify automatic chunk splitting works for large months
- Test that API limit warnings are logged correctly

### Step 2.5: Enhanced Chunking Strategy (Future Enhancement)

**For months exceeding 10,000 records:**

- Implement automatic splitting into weekly/bi-weekly chunks
- Or integrate with export endpoints for very large date ranges
- Consider using `/Exports/Order/Csv` for months with >50,000 records

**Implementation Options:**

1. **Weekly chunks:** Split month into 4-5 weekly chunks
2. **Bi-weekly chunks:** Split month into 2 bi-weekly chunks
3. **Export endpoint integration:** Use async export endpoints for large ranges
4. **Hybrid approach:** Use search API for small months, export API for large ones

## Phase 3: Query Layer Integration (Week 2)

### Step 3.1: Database Query Interface

- Create `DatabaseQueryClient` class in `queries.py`
- Implement `search_occurrences()` method matching UnifiedAPIClient signature
- Add date range queries
- Add species filtering
- Add location filtering (lat/lon, area)
- Support pagination (limit/offset)

**Interface design:**

- Match UnifiedAPIClient.search_occurrences() signature exactly
- Return same response format (normalized)
- Add `_data_source: "database"` field

**Files to create:**

- `src/database/queries.py`

**Validation:**

- Test query interface matches API client
- Verify response format compatibility
- Test filtering works correctly

### Step 3.2: Integration with UnifiedAPIClient

- Modify `UnifiedAPIClient` to check DuckDB first for historical queries
- Add database client initialization
- Implement smart routing logic:
  - Date range older than 30 days → DuckDB
  - Date range includes recent data → Artportalen API
  - No database → Fallback to API
- Preserve backward compatibility (API-only mode)

**Routing logic:**

- Check if database exists and has data
- Query database for historical portions
- Query API for recent portions
- Merge results if date range spans both

**Files to modify:**

- `src/api/unified_client.py`

**Validation:**

- Test routing logic with various date ranges
- Verify backward compatibility (no database)
- Test mixed date ranges (historical + recent)

### Step 3.3: Response Format Normalization

- Ensure database queries return same format as API clients
- Use existing `normalize_artportalen_response()` where possible
- Add database-specific normalization if needed
- Maintain field consistency across all sources

**Files to modify:**

- `src/database/queries.py`
- `src/api/data_adapter.py` (if needed)

**Validation:**

- Compare database response format with API responses
- Verify all expected fields present
- Test response handling in app.py

## Phase 4: Testing & Validation (Week 2-3)

### Step 4.1: Unit Tests

- Test database connection
- Test schema creation
- Test data ingestion
- Test query interface
- Test integration with UnifiedAPIClient

**Test files to create:**

- `tests/test_database_connection.py`
- `tests/test_database_schema.py`
- `tests/test_database_ingestion.py`
- `tests/test_database_queries.py`
- `tests/test_unified_client_integration.py`

**Validation:**

- Run all tests
- Achieve >80% code coverage
- Fix any failing tests

### Step 4.2: Integration Tests

- Test end-to-end data flow: API → Database → Query
- Test date range queries spanning database and API
- Test fallback behavior when database unavailable
- Test data freshness (recent data from API)

**Test scenarios:**

- Historical query (database only)
- Recent query (API only)
- Mixed query (database + API)
- Database unavailable (fallback to API)

**Files to create:**

- `tests/test_database_integration.py`

**Validation:**

- All integration tests pass
- Verify fallback behavior works
- Test error scenarios

### Step 4.3: Performance Testing

- Benchmark query performance (DuckDB vs API)
- Test with various date ranges (1 year, 5 years, 20 years)
- Test with different filters (species, location)
- Measure query times and compare

**Metrics to track:**

- Query response time
- Database size
- Memory usage
- Concurrent query performance

**Validation:**

- Document performance improvements
- Verify queries are faster than API calls
- Test with realistic data volumes

### Step 4.4: Data Validation

- Verify data completeness (all expected records present)
- Verify data accuracy (compare sample records with API)
- Check date ranges are correct
- Verify species counts match expectations
- Check coordinate data quality

**Validation steps:**

- Spot-check random records
- Compare aggregated counts with API
- Verify date distributions
- Check for duplicate records

**Files to create:**

- `scripts/validate_data.py`

**Validation:**

- Data validation script passes
- Document any discrepancies
- Fix data quality issues

## Phase 5: Streamlit App Integration (Week 3)

### Step 5.1: Configuration Updates

- Add database configuration to `Config` class
- Add database path setting (with default)
- Add feature flag for database usage
- Add database initialization check

**Files to modify:**

- `src/config.py`

**Validation:**

- Configuration loads correctly
- Defaults work as expected
- Feature flag works

### Step 5.2: App Initialization Updates

- Update `init_session_state()` to initialize database client
- Add database availability check
- Handle database initialization errors gracefully
- Preserve backward compatibility (app works without database)

**Files to modify:**

- `src/app.py`

**Validation:**

- App starts successfully with database
- App starts successfully without database
- Database errors don't crash app

### Step 5.3: UI Updates

- Add database status indicator (if data available)
- Show data source information (database vs API)
- Add admin section for database management (optional)
- Update search results to show data source

**UI features:**

- Status badge showing database availability
- Info message when using database
- Date range indicator (historical vs recent)

**Files to modify:**

- `src/app.py`

**Validation:**

- UI updates render correctly
- Status indicators accurate
- No UI regressions

### Step 5.4: Browser Testing

- Test search functionality with database
- Test search functionality without database (fallback)
- Test date range searches (historical, recent, mixed)
- Test species filtering
- Test location filtering
- Verify map display works
- Verify table display works
- Test pagination
- Test download functionality

**Browser test scenarios:**

- Historical date range (2005-2010) → Should use database
- Recent date range (last 7 days) → Should use API
- Mixed date range (2020-2025) → Should use database + API
- No database available → Should use API only
- Verify UI shows correct data source

**Files to test:**

- `src/app.py` (all search flows)

**Validation:**

- All browser tests pass
- No UI regressions
- Performance acceptable
- User experience smooth

## Phase 6: Historical Data Loading (Week 3-4)

### Step 6.1: Full Historical Data Load

- Load 20 years of data (2005-2025) using ingestion script
- Process in batches (monthly chunks)
- Monitor progress and errors
- Handle rate limiting and API errors gracefully
- Resume capability for interrupted loads

**Loading strategy:**

- Start with 2005-2010 (5 years) for testing
- Gradually expand to full 20 years
- Monitor API rate limits
- Track progress in log file

**Files to use:**

- `scripts/load_historical_data.py`

**Validation:**

- Verify data loads successfully
- Check data completeness
- Verify no duplicates
- Test query performance

### Step 6.2: Data Quality Assurance

- Run data validation script
- Verify record counts
- Check date ranges
- Verify species distributions
- Check coordinate data quality
- Identify and fix data issues

**Validation steps:**

- Compare total counts with expected
- Verify date distributions
- Check species names are correct
- Verify coordinate data is valid

**Files to use:**

- `scripts/validate_data.py`

**Validation:**

- Data validation passes
- Document any issues found
- Fix critical issues

### Step 6.3: Performance Optimization

- Analyze query performance
- Optimize indexes if needed
- Add additional indexes for common queries
- Test query performance with full dataset
- Measure storage size

**Optimization tasks:**

- Review slow queries
- Add indexes for common filters
- Optimize date range queries
- Test aggregation queries

**Validation:**

- Query performance acceptable
- Storage size reasonable
- Indexes effective

## Phase 7: Incremental Updates (Week 4)

### Step 7.1: Update Mechanism

- Create daily update script
- Fetch last 30 days from Artportalen API
- Upsert into database (update existing, insert new)
- Handle deduplication
- Add logging

**Update strategy:**

- Run daily (or weekly initially)
- Fetch last 30 days to ensure coverage
- Use upsert logic (ON CONFLICT UPDATE)
- Track update timestamps

**Files to create:**

- `scripts/update_database.py`

**Validation:**

- Update script works correctly
- No duplicates created
- Updates are incremental
- Errors handled gracefully

### Step 7.2: Automated Updates

- Add scheduled task capability (optional)
- Document manual update process
- Add update status tracking
- Create update monitoring

**Automation options:**

- Cron job (Linux/Mac)
- Scheduled task (Windows)
- Streamlit scheduler (if available)
- Manual trigger (recommended initially)

**Files to create:**

- `scripts/update_database.py` (enhance)

**Validation:**

- Update process works
- Can be run manually
- Can be scheduled (if implemented)

## Phase 8: Final Testing & Documentation (Week 4)

### Step 8.1: Comprehensive Browser Testing

- Test all search scenarios
- Test with and without database
- Test error scenarios
- Test performance with large date ranges
- Verify all existing functionality still works
- Test edge cases

**Browser test checklist:**

- [ ] Historical search (2005-2010) works
- [ ] Recent search (last 7 days) works
- [ ] Mixed date range works
- [ ] Species filtering works
- [ ] Location filtering works
- [ ] Map display works
- [ ] Table display works
- [ ] Download works
- [ ] Pagination works
- [ ] No database fallback works
- [ ] Error handling works
- [ ] Performance acceptable

**Validation:**

- All browser tests pass
- No regressions
- User experience smooth

### Step 8.2: Documentation

- Update README with database setup instructions
- Document database schema
- Document ingestion process
- Document update process
- Add troubleshooting guide

**Documentation to create/update:**

- README.md (database section)
- `docs/DATABASE_SETUP.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/DATA_INGESTION.md`
  - Document API limits and constraints
  - Explain chunk splitting strategy
  - Document export endpoint usage for large datasets

**Validation:**

- Documentation complete
- Instructions clear
- Examples provided

### Step 8.3: Code Cleanup

- Review all code for quality
- Add missing docstrings
- Remove debug code
- Optimize imports
- Run linters and fix issues

**Validation:**

- Code quality acceptable
- No linting errors
- Documentation complete

## Success Criteria

1. ✅ DuckDB database successfully stores 20 years of bird observation data
2. ✅ Queries are significantly faster than API calls (>10x improvement)
3. ✅ All existing functionality works unchanged (backward compatibility)
4. ✅ Smart routing works correctly (database for historical, API for recent)
5. ✅ Browser tests pass for all scenarios
6. ✅ Performance is acceptable for user experience
7. ✅ Documentation is complete and clear
8. ✅ Incremental updates work correctly
9. ✅ Error handling is robust
10. ✅ No regressions in existing features
11. ✅ API limits are properly handled (10,000 records per query)
12. ✅ Large months (>10,000 records) are handled correctly (warnings logged, chunk splitting works)

## Risk Mitigation

**Risks:**

1. **API rate limiting** - Mitigate with batch processing, delays, retry logic
2. **API record limits (10,000 per query)** - Mitigate with automatic chunk splitting, export endpoints for large ranges
3. **Data quality issues** - Mitigate with validation scripts, spot checks
4. **Storage size** - Mitigate with compression, monitoring, cleanup
5. **Performance issues** - Mitigate with indexes, query optimization, testing
6. **Breaking existing functionality** - Mitigate with comprehensive testing, feature flags
7. **Incomplete data for large months** - Mitigate with chunk splitting, export endpoints, clear logging

**Mitigation strategies:**

- Feature flag for database usage (can disable if issues)
- Comprehensive test suite
- Gradual rollout (test with small dataset first)
- Backup and restore capability
- Monitoring and logging

## File Structure

```
src/
  database/
    __init__.py
    connection.py      # Database connection manager
    schema.py          # Schema definitions and migrations
    ingestion.py       # Data ingestion pipeline
    queries.py          # Query interface
    
scripts/
  load_historical_data.py    # Historical data loading script
  update_database.py         # Incremental update script
  validate_data.py          # Data validation script
  
tests/
  test_database_connection.py
  test_database_schema.py
  test_database_ingestion.py
  test_database_queries.py
  test_unified_client_integration.py
  test_database_integration.py
  
docs/
  DATABASE_SETUP.md
  DATABASE_SCHEMA.md
  DATA_INGESTION.md
```

## Timeline Estimate

- **Week 1**: Foundation & Setup + Ingestion Framework
- **Week 2**: Query Layer + Integration + Testing
- **Week 3**: App Integration + Browser Testing + Historical Load (partial)
- **Week 4**: Full Historical Load + Updates + Final Testing + Documentation

**Total: 4 weeks** (can be adjusted based on data volume and API rate limits)