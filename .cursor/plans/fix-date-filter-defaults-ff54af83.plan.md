<!-- ff54af83-e844-4e97-a2fd-199fa9860ec9 f430c23f-4002-4beb-aac5-95ceeba45245 -->
# Dual API Integration: Artportalen + GBIF

## Overview

Integrate Artportalen API for real-time observations while maintaining GBIF API for historical data. Automatically select the appropriate API based on date range, with unified data handling and optional manual API selection.

## Key Differences

### Artportalen API

- **Update Frequency**: ~10 minutes (near real-time)
- **Authentication**: Required (API key from api-portal.artdatabanken.se)
- **Coverage**: Current day + recent observations
- **Access**: Requires registration and subscription

### GBIF API (Current)

- **Update Frequency**: Weekly updates
- **Authentication**: None required (public)
- **Coverage**: Historical data (older than ~1 week)
- **Access**: Public, no registration needed

## Architecture

### 1. API Client Layer

- **File**: `src/api_client.py` → Refactor into separate modules
  - Create `src/api/gbif_client.py` - Existing GBIF client
  - Create `src/api/artportalen_client.py` - New Artportalen client
  - Create `src/api/unified_client.py` - Smart router that selects API based on date range

### 2. Configuration

- **File**: `src/config.py`
  - Add Artportalen API base URL (from api-portal.artdatabanken.se documentation)
  - Add API key configuration (optional, with fallback to GBIF if not set)
  - Add date threshold for API selection (e.g., 7-14 days)
  - Add birds taxon ID for Artportalen (different from GBIF taxon key)

### 3. Data Normalization

- **File**: `src/api/data_adapter.py`
  - Create adapter functions to normalize Artportalen response format to match GBIF format
  - Map Artportalen fields to GBIF field names:
    - `eventDate` → `eventDate`
    - `scientificName` → `species`/`scientificName`
    - `vernacularName` → `vernacularName`
    - `locality` → `locality`
    - `stateProvince` → `stateProvince`
    - Coordinates mapping
    - Date parsing (Artportalen may use different format)

### 4. UI Updates

- **File**: `src/app.py`
  - Add API source selector in sidebar (auto/manual selection)
  - Update `search_observations()` to use unified client
  - Update `format_observation_record()` to handle normalized data from both APIs
  - Update UI text to indicate data source (Artportalen real-time vs GBIF historical)
  - Add info message about API selection logic

### 5. Error Handling

- Handle Artportalen API authentication failures gracefully
- Fallback to GBIF if Artportalen API unavailable or unauthenticated
- Clear error messages for users about API availability

## Implementation Steps

### Phase 1: Research & Setup

1. **Register for Artportalen API Access**

   - Create account on api-portal.artdatabanken.se
   - Subscribe to observation API product
   - Obtain API key
   - Review API documentation for endpoints and parameters

2. **Research API Endpoints**

   - Identify observation search endpoint (likely `Sightings_GetSightingsBySearch` or similar)
   - Document required parameters (dateFrom, dateTo, taxonIds, region filters)
   - Document response structure
   - Identify rate limits and usage policies

### Phase 2: Artportalen Client Implementation

3. **Create Artportalen API Client**

   - Implement `ArtportalenAPIClient` class
   - Add authentication headers (API key)
   - Implement `search_observations()` method matching GBIF interface
   - Handle API errors and rate limiting
   - Add retry logic for transient failures

4. **Test Artportalen Client**

   - Test with recent dates (last 7 days)
   - Verify authentication works
   - Test filtering parameters (date range, location, species)
   - Verify response structure

### Phase 3: Data Normalization

5. **Create Data Adapter**

   - Map Artportalen response fields to GBIF format
   - Handle date format differences
   - Normalize coordinate fields
   - Ensure consistent field names across both APIs

6. **Test Data Normalization**

   - Compare normalized Artportalen data with GBIF data
   - Verify all required fields are present
   - Test edge cases (missing fields, null values)

### Phase 4: Unified Client

7. **Create Unified Client**

   - Implement `UnifiedAPIClient` class
   - Add logic to select API based on date range:
     - Recent dates (last 7-14 days) → Artportalen API
     - Historical dates (older) → GBIF API
   - Handle fallback: if Artportalen unavailable/unauthenticated → use GBIF
   - Support manual API selection override

8. **Update Existing Code**

   - Refactor `GBIFAPIClient` into separate module
   - Update `init_session_state()` to use unified client
   - Update `search_observations()` to use unified client
   - Ensure backward compatibility

### Phase 5: UI Updates

9. **Add API Selection UI**

   - Add radio button/select in sidebar: "Auto", "Artportalen (Real-time)", "GBIF (Historical)"
   - Show current API being used in search results
   - Add info tooltip explaining API selection logic

10. **Update Messages**

    - Update "Searching GBIF..." message to reflect actual API
    - Update info messages about data freshness
    - Update footer to show both data sources

### Phase 6: Configuration & Documentation

11. **Update Configuration**

    - Add Artportalen API base URL
    - Add API key configuration (optional, with instructions)
    - Add date threshold configuration
    - Document setup requirements in README

12. **Update Documentation**

    - Update README with dual API support
    - Document Artportalen API setup process
    - Add troubleshooting section for API key issues
    - Update API information section

### Phase 7: Testing & Validation

13. **Test Dual API Integration**

    - Test with recent dates (should use Artportalen)
    - Test with historical dates (should use GBIF)
    - Test with date range spanning threshold
    - Test fallback when Artportalen unavailable
    - Test manual API selection

14. **Test Data Consistency**

    - Verify normalized data displays correctly
    - Test map rendering with both APIs
    - Test CSV export with both APIs
    - Verify field mappings are correct

## File Structure Changes

```
src/
├── api/
│   ├── __init__.py
│   ├── gbif_client.py          # Refactored GBIF client
│   ├── artportalen_client.py  # New Artportalen client
│   ├── unified_client.py      # Smart API router
│   └── data_adapter.py        # Data normalization
├── app.py                     # Updated to use unified client
├── config.py                  # Updated with Artportalen config
└── __init__.py
```

## Configuration Requirements

### Required

- Artportalen API key (optional - app falls back to GBIF if not set)
- Artportalen API base URL (from documentation)
- Date threshold for API selection (default: 7 days)

### Optional

- Rate limiting configuration
- Cache configuration for API responses
- Retry policy configuration

## Error Handling Strategy

1. **Artportalen API Unavailable**

   - Fallback to GBIF API automatically
   - Log warning message
   - Show user-friendly message in UI

2. **Authentication Failure**

   - Fallback to GBIF API
   - Log error
   - Show message about API key configuration

3. **Rate Limiting**

   - Implement exponential backoff
   - Fallback to GBIF if Artportalen rate limited
   - Show user message about rate limits

## Future Enhancements

- Cache recent Artportalen responses to reduce API calls
- Combine results from both APIs for date ranges spanning threshold
- Add data source indicator in observation cards
- Show data freshness timestamp
- Support for filtering protected observations (Artportalen)

## References

- Artportalen Developer Portal: https://api-portal.artdatabanken.se/
- Artportalen API Documentation: https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/
- GBIF API Documentation: https://techdocs.gbif.org/en/openapi/
- Terms and Conditions: https://www.slu.se/en/slu-swedish-species-information-centre/rapportering-och-fynddata/oppna-data-och-apier/terms-and-conditions-for-the-apis/

### To-dos

- [ ] Research Artportalen API endpoints, authentication, and response structure. Register for API access and obtain API key.
- [ ] Create ArtportalenAPIClient class with authentication and search_occurrences method matching GBIF interface.
- [ ] Create data adapter to normalize Artportalen response format to match GBIF format structure.
- [ ] Refactor existing GBIFAPIClient into separate module (src/api/gbif_client.py).
- [ ] Create UnifiedAPIClient that selects API based on date range (recent = Artportalen, historical = GBIF).
- [ ] Add Artportalen API configuration (base URL, API key, date threshold) to config.py.
- [ ] Update app.py to use UnifiedAPIClient instead of GBIFAPIClient directly.
- [ ] Add API source selector in sidebar UI (auto/manual selection) and show current API in results.
- [ ] Update README with Artportalen API setup instructions and dual API usage documentation.
- [ ] Test dual API integration: recent dates (Artportalen), historical dates (GBIF), fallback scenarios, and data normalization.