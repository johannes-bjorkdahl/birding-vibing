# Database Schema Documentation

This document describes the DuckDB database schema for bird observations.

## Overview

The database stores normalized bird observation data from Artportalen API. The schema is designed for fast analytical queries while maintaining compatibility with API response formats.

## Schema Version

Current schema version: **1**

The schema version is tracked in the `schema_version` table for migration support.

## Tables

### `observations`

Main table storing bird observation records.

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | TEXT | NO | Primary key - Unique observation identifier from API |
| `observation_date` | DATE | NO | Date of observation |
| `species_name` | TEXT | NO | Common name of the species |
| `species_scientific` | TEXT | YES | Scientific name of the species |
| `latitude` | DOUBLE | NO | Latitude coordinate (decimal degrees) |
| `longitude` | DOUBLE | NO | Longitude coordinate (decimal degrees) |
| `location_name` | TEXT | YES | Human-readable location name |
| `observer_name` | TEXT | YES | Name of observer (if available) |
| `quantity` | INTEGER | YES | Number of individuals observed |
| `verification_status` | TEXT | YES | Verification status (e.g., "Verified", "Unverified") |
| `habitat` | TEXT | YES | Habitat type |
| `coordinate_uncertainty` | DOUBLE | YES | Coordinate uncertainty in meters |
| `api_source` | TEXT | NO | Source API (e.g., "artportalen", "gbif") |
| `created_at` | TIMESTAMP | YES | Record creation timestamp |
| `updated_at` | TIMESTAMP | YES | Record last update timestamp |

#### Constraints

- Primary Key: `id` (unique constraint)
- Not Null: `id`, `observation_date`, `species_name`, `latitude`, `longitude`, `api_source`

#### Indexes

The following indexes are created for query optimization:

1. **`idx_observation_date`** - Index on `observation_date`
   - Optimizes date range queries
   - Used for filtering by date

2. **`idx_species_name`** - Index on `species_name`
   - Optimizes species filtering
   - Used for species-specific queries

3. **`idx_location`** - Composite index on `(latitude, longitude)`
   - Optimizes spatial queries
   - Used for location-based filtering

4. **`idx_date_species`** - Composite index on `(observation_date, species_name)`
   - Optimizes combined date and species queries
   - Used for time-series analysis by species

5. **`idx_api_source`** - Index on `api_source`
   - Optimizes API source filtering
   - Used for filtering by data source

### `schema_version`

Table tracking database schema versions for migration support.

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `version` | INTEGER | NO | Schema version number (primary key) |
| `applied_at` | TIMESTAMP | YES | Timestamp when version was applied |

## Data Types

### Date Handling

- **`observation_date`**: Stored as DATE type
  - Format: `YYYY-MM-DD`
  - Range: Typically 2005-2025 (historical data)

### Coordinate Handling

- **`latitude`**: Decimal degrees, range -90 to 90
- **`longitude`**: Decimal degrees, range -180 to 180
- **`coordinate_uncertainty`**: Meters, can be NULL

### Text Fields

- **`species_name`**: Common name (e.g., "Koltrast")
- **`species_scientific`**: Scientific name (e.g., "Turdus merula")
- **`location_name`**: Free-form location description
- **`api_source`**: Source identifier ("artportalen", "gbif", "database")

## Data Transformation

Data from Artportalen API is transformed using `transform_artportalen_to_db_record()`:

### Mapping

- `occurrenceId` → `id`
- `event.startDate` → `observation_date` (extracted date)
- `taxon.vernacularName` → `species_name`
- `taxon.scientificName` → `species_scientific`
- `location.decimalLatitude` → `latitude`
- `location.decimalLongitude` → `longitude`
- `location.locality` → `location_name`
- `occurrence.recordedBy` → `observer_name`
- `occurrence.individualCount` → `quantity`
- `identification.verificationStatus` → `verification_status`
- `location.coordinateUncertaintyInMeters` → `coordinate_uncertainty`

### Normalization

- Dates are extracted from ISO 8601 strings
- Coordinates are validated and converted to double
- Null values are handled appropriately
- Missing fields are set to NULL

## Query Patterns

### Common Queries

1. **Date Range Query**
```sql
SELECT * FROM observations
WHERE observation_date BETWEEN '2020-01-01' AND '2020-12-31'
ORDER BY observation_date DESC
LIMIT 100;
```

2. **Species Query**
```sql
SELECT * FROM observations
WHERE species_name = 'Koltrast'
ORDER BY observation_date DESC;
```

3. **Location Query**
```sql
SELECT * FROM observations
WHERE latitude BETWEEN 57.0 AND 58.0
  AND longitude BETWEEN 11.0 AND 12.0;
```

4. **Combined Query**
```sql
SELECT species_name, COUNT(*) as count
FROM observations
WHERE observation_date BETWEEN '2020-01-01' AND '2020-12-31'
GROUP BY species_name
ORDER BY count DESC;
```

## Performance Considerations

### Index Usage

- Always filter by indexed columns when possible
- Use date ranges for efficient filtering
- Composite indexes help with multi-column queries

### Query Optimization

- Use `LIMIT` for large result sets
- Use `ORDER BY` with indexed columns
- Consider date range partitioning for very large datasets

### Storage

- Estimated size: ~100-200 bytes per record
- 20 years of data: ~1-2 GB total
- Indexes add ~20-30% overhead

## Migration Strategy

Schema versioning allows for future migrations:

1. **Version Check**: `get_schema_version()` checks current version
2. **Migration**: If version mismatch, run migration scripts
3. **Version Update**: Update `schema_version` table after migration

Future migrations might include:
- Additional columns
- Index modifications
- Data type changes
- Table restructuring

## Validation

Use `scripts/validate_data.py` to validate:
- Schema integrity
- Data completeness
- Data quality
- Coordinate validity
- Duplicate detection

## Backup and Recovery

### Schema Backup

To backup schema definition:

```sql
-- Export schema
EXPORT DATABASE 'schema_backup' (FORMAT SQL);
```

### Data Backup

See [Database Setup Guide](DATABASE_SETUP.md#backup-and-recovery) for backup procedures.

## Related Documentation

- [Database Setup Guide](DATABASE_SETUP.md)
- [Data Ingestion Guide](DATA_INGESTION.md)
- [API Troubleshooting Guide](API_TROUBLESHOOTING.md)

