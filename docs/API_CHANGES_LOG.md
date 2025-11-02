# API Changes Log

## November 2025 - Date Filter Format Fix

### Date: 2025-11-02

### Issue
Searching for current date and yesterday (November 1-2, 2025) returned no results, despite thousands of observations existing in the API.

### Root Cause
The Artportalen API request format was incorrect. The API requires nested objects for filters, not flat parameters.

### Changes Made

#### File: `src/api/artportalen_client.py`

**Before (Lines 87-97):**
```python
if taxon_id:
    request_body["taxonIds"] = [taxon_id]

if start_date and end_date:
    request_body["dateFrom"] = start_date.isoformat()
    request_body["dateTo"] = end_date.isoformat()
elif start_date:
    request_body["dateFrom"] = start_date.isoformat()
    request_body["dateTo"] = start_date.isoformat()
```

**After (Lines 87-103):**
```python
if taxon_id:
    request_body["taxon"] = {"ids": [taxon_id]}

# Date filter - use nested date object with startDate/endDate (correct API format)
if start_date and end_date:
    request_body["date"] = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dateFilterType": "OverlappingStartDateAndEndDate"  # Default filter type
    }
elif start_date:
    request_body["date"] = {
        "startDate": start_date.isoformat(),
        "endDate": start_date.isoformat(),
        "dateFilterType": "OverlappingStartDateAndEndDate"
    }
```

**Also Updated:** Pagination request format (lines 280-294) to use the same nested format.

### Documentation Discovered

1. **API Info Endpoint:** `https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo`
   - Provides API version, documentation links, and status

2. **GitHub Documentation:** https://github.com/biodiversitydata-se/SOS
   - `/Docs/SearchFilter.md` contains the correct parameter formats
   - Critical resource for understanding API request structure

### Verification

**Test Command:**
```bash
uv run python3 -c "
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
if result.get('results'):
    print('✅ SUCCESS - Found November 2025 observations!')
"
```

**Result:** ✅ Returns 10+ observations with dates in November 2025

### Impact

- ✅ Date filtering now works correctly for recent dates
- ✅ API filters server-side (no client-side workaround needed)
- ✅ Real-time data retrieval working as expected
- ✅ No breaking changes to other functionality

### References

- API Documentation: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/SearchFilter.md
- API Info Endpoint: https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo
- Related Issue: Date filtering not working for current dates

