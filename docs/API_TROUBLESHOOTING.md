# Artportalen API Troubleshooting Guide

## Quick Reference: API Information Sources

### 1. API Info Endpoint
**Endpoint:** `https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo`

This endpoint provides basic API metadata:
- API name and version
- Release date
- Link to GitHub documentation
- API status

**Usage:**
```python
import httpx
headers = {'Ocp-Apim-Subscription-Key': YOUR_API_KEY, 'Accept': 'application/json'}
response = httpx.get('https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo', headers=headers)
info = response.json()
# Returns: apiName, apiVersion, apiReleased, apiDocumentation (GitHub link), apiChangelog, apiStatus
```

### 2. GitHub Documentation
**Repository:** https://github.com/biodiversitydata-se/SOS

**Key Documentation Files:**
- **Search Filter Parameters:** `/Docs/SearchFilter.md` - **CRITICAL** for understanding request format
- **Endpoints:** `/Docs/Endpoints.md` - API endpoint documentation
- **Observation Structure:** `/Docs/Observation.md` - Response structure
- **Field Sets:** `/Docs/FieldSets.md` - Available fields
- **Changelog:** `/CHANGELOG.md` - API changes over time

**Access Pattern:**
1. Go to https://github.com/biodiversitydata-se/SOS
2. Navigate to `Docs/SearchFilter.md` for filter parameters
3. Navigate to `Docs/Endpoints.md` for endpoint details

## Critical API Format Information

### Date Filter Format (FIXED - November 2025)

**❌ INCORRECT (Old Format):**
```json
{
  "taxonIds": [100012],
  "dateFrom": "2025-11-01",
  "dateTo": "2025-11-02"
}
```

**✅ CORRECT (Current Format):**
```json
{
  "taxon": {
    "ids": [100012]
  },
  "date": {
    "startDate": "2025-11-01",
    "endDate": "2025-11-02",
    "dateFilterType": "OverlappingStartDateAndEndDate"
  }
}
```

### Date Filter Types

The API supports different date filter types (from SearchFilter.md):

1. **OverlappingStartDateAndEndDate** (Default)
   - Returns observations where `startDate <= endDate` AND `endDate >= startDate`
   - Use for: Finding observations that overlap with a date range

2. **BetweenStartDateAndEndDate**
   - Returns observations where `startDate >= startDate` AND `endDate <= endDate`
   - Use for: Finding observations completely within a date range

3. **OnlyStartDate**
   - Returns observations where `startDate` is between the filter dates
   - Use for: Filtering by observation start date only

4. **OnlyEndDate**
   - Returns observations where `endDate` is between the filter dates
   - Use for: Filtering by observation end date only

## What Was Fixed (November 2025)

### Problem
- Searching for current date and yesterday returned no results
- User reported thousands of observations exist for November 2025
- Date filtering appeared to not work

### Root Cause
The API request format was incorrect:
1. Used `taxonIds` instead of nested `taxon.ids`
2. Used `dateFrom`/`dateTo` instead of nested `date.startDate`/`date.endDate`
3. Missing `dateFilterType` parameter

### Solution
Updated `src/api/artportalen_client.py` to use the correct nested object format:
- Changed `taxonIds` → `taxon: {ids: [...]}`
- Changed `dateFrom`/`dateTo` → `date: {startDate, endDate, dateFilterType}`

### Files Modified
- `src/api/artportalen_client.py`:
  - Lines 87-103: Updated request body format for taxon and date filters
  - Lines 280-294: Updated pagination request format to match

## How It Works Now

### Request Flow
1. User selects date range (e.g., Nov 1-2, 2025)
2. `ArtportalenAPIClient.search_occurrences()` is called
3. Request body is built with correct nested format:
   ```python
   {
       "skip": 0,
       "take": 100,
       "taxon": {"ids": [100012]},
       "date": {
           "startDate": "2025-11-01",
           "endDate": "2025-11-02",
           "dateFilterType": "OverlappingStartDateAndEndDate"
       }
   }
   ```
4. API filters server-side (no client-side filtering needed for recent dates)
5. Results are normalized and returned

### Date Filtering Behavior
- **Server-side filtering:** The API correctly filters by date when using the proper format
- **No pagination needed:** For recent dates, the API returns filtered results directly
- **Fallback pagination:** Still implemented for edge cases, but typically not needed

## Instructions for Future Cursor Agents

### When Troubleshooting API Issues

#### Step 1: Check API Info Endpoint
```python
# Always start by checking the API info endpoint
api_info_url = 'https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo'
# This will give you version, documentation links, and status
```

#### Step 2: Consult GitHub Documentation
1. Navigate to: https://github.com/biodiversitydata-se/SOS
2. Check `/Docs/SearchFilter.md` for filter parameter formats
3. Check `/Docs/Endpoints.md` for endpoint details
4. Check `/CHANGELOG.md` for recent changes

#### Step 3: Verify Request Format
**Key things to check:**
- Are date filters using nested `date` object? (NOT `dateFrom`/`dateTo`)
- Are taxon filters using nested `taxon` object? (NOT `taxonIds`)
- Is `dateFilterType` specified? (Default: "OverlappingStartDateAndEndDate")

#### Step 4: Test Directly
```python
# Test the API request format directly
import httpx
headers = {
    'Ocp-Apim-Subscription-Key': Config.ARTPORTALEN_API_KEY,
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}
payload = {
    "skip": 0,
    "take": 10,
    "taxon": {"ids": [100012]},  # Note: nested object
    "date": {  # Note: nested object
        "startDate": "2025-11-01",
        "endDate": "2025-11-02",
        "dateFilterType": "OverlappingStartDateAndEndDate"
    }
}
response = httpx.post(
    'https://api.artdatabanken.se/species-observation-system/v1/Observations/Search',
    json=payload,
    headers=headers
)
```

### Common Issues and Solutions

#### Issue: No results for recent dates
**Check:**
1. Request format (nested objects vs flat parameters)
2. Date format (ISO format: YYYY-MM-DD)
3. API key validity
4. Date filter type (try different types if needed)

#### Issue: Results from wrong dates
**Check:**
1. Date filter format (must be nested `date` object)
2. `dateFilterType` matches intended behavior
3. API response parsing (check `event.startDate` field)

#### Issue: API returns all records regardless of filters
**Likely cause:** Using wrong parameter names (old format)
**Solution:** Use nested object format as documented

### Key Files to Reference

1. **`src/api/artportalen_client.py`**
   - Lines 87-103: Correct request format
   - Lines 145-239: Response normalization
   - Lines 240-313: Pagination logic (if needed)

2. **`src/api/data_adapter.py`**
   - `normalize_artportalen_record()`: Maps API response to GBIF-like format
   - Handles nested structures: `event.startDate`, `taxon.scientificName`, `location.decimalLatitude`, etc.

3. **`src/config.py`**
   - `ARTPORTALEN_API_BASE_URL`: Base URL for API
   - `ARTPORTALEN_BIRDS_TAXON_ID`: Taxon ID for birds (100012)

### Testing Checklist

When making changes to API integration:

- [ ] Check `ApiInfo` endpoint for current API version
- [ ] Review GitHub `SearchFilter.md` for parameter formats
- [ ] Test request format directly with `httpx`
- [ ] Verify date filtering works for recent dates (current date)
- [ ] Verify date filtering works for historical dates
- [ ] Check that results are correctly normalized
- [ ] Verify map displays coordinates correctly
- [ ] Test pagination if large result sets are expected

### Debugging Commands

```python
# Check API info
python3 -c "
import httpx
from src.config import Config
headers = {'Ocp-Apim-Subscription-Key': Config.ARTPORTALEN_API_KEY, 'Accept': 'application/json'}
r = httpx.get('https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo', headers=headers)
print(r.json())
"

# Test date filtering
python3 -c "
from src.api.artportalen_client import ArtportalenAPIClient
from src.config import Config
from datetime import date, timedelta
client = ArtportalenAPIClient(Config.ARTPORTALEN_API_BASE_URL, Config.ARTPORTALEN_API_KEY)
today = date.today()
yesterday = today - timedelta(days=1)
result = client.search_occurrences(
    taxon_id=Config.ARTPORTALEN_BIRDS_TAXON_ID,
    start_date=yesterday,
    end_date=today,
    limit=10
)
print(f'Results: {result.get(\"count\", 0)}')
"
```

### Location Filter Format (FIXED - November 2025)

**❌ INCORRECT (Old Format):**
```json
{
  "province": "Västra Götaland",
  "locality": "Göteborg"
}
```

**✅ CORRECT (Current Format):**
```json
{
  "geographics": {
    "areas": [
      {
        "areaType": "County",
        "featureId": "14"
      }
    ]
  }
}
```

For municipalities:
```json
{
  "geographics": {
    "areas": [
      {
        "areaType": "Municipality",
        "featureId": "1480"
      }
    ]
  }
}
```

**Key Points:**
- Location filters MUST use nested `geographics` object with `areas` array
- Each area requires `areaType` ("County" or "Municipality") and `featureId` (numeric ID as string)
- Feature IDs are mapped from location names using static mappings in `src/locations.py`
- Counties: Use `areaType: "County"` with county feature ID (e.g., "14" for Västra Götaland)
- Municipalities: Use `areaType: "Municipality"` with municipality feature ID (e.g., "1480" for Göteborg)
- Multiple areas can be included in the array for filtering across multiple locations

**Feature ID Lookup:**
- County feature IDs are mapped in `COUNTY_FEATURE_IDS` dictionary
- Municipality feature IDs are mapped in `MUNICIPALITY_FEATURE_IDS` dictionary (partial mapping)
- See `src/locations.py` for complete mappings and lookup functions
- Full feature ID lists available in Areas.md documentation: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/Areas.md

## Summary

**Always remember:**
1. The Artportalen API uses **nested objects** for filters, not flat parameters
2. Date filters: `date: {startDate, endDate, dateFilterType}` (NOT `dateFrom`/`dateTo`)
3. Taxon filters: `taxon: {ids: [...]}` (NOT `taxonIds`)
4. Location filters: `geographics: {areas: [{areaType, featureId}]}` (NOT `province`/`locality`)
5. Check GitHub documentation (`/Docs/SearchFilter.md`) for the latest format
6. Use `ApiInfo` endpoint to verify API version and documentation links

**Current Working Format (as of November 2025):**
```json
{
  "skip": 0,
  "take": 100,
  "taxon": {"ids": [100012]},
  "date": {
    "startDate": "2025-11-01",
    "endDate": "2025-11-02",
    "dateFilterType": "OverlappingStartDateAndEndDate"
  },
  "geographics": {
    "areas": [
      {
        "areaType": "Municipality",
        "featureId": "1480"
      }
    ]
  }
}
```

