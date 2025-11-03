"""Database query interface for DuckDB.

Provides query methods matching the UnifiedAPIClient interface
for seamless integration.
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal
from src.api.data_adapter import normalize_artportalen_record

logger = logging.getLogger(__name__)


class DatabaseQueryClient:
    """Query client for DuckDB database.
    
    Provides methods matching UnifiedAPIClient.search_occurrences()
    signature for compatibility.
    """
    
    def __init__(self, connection):
        """Initialize the database query client.
        
        Args:
            connection: DuckDB connection instance
        """
        self.connection = connection
        logger.info("Database query client initialized")
    
    def search_occurrences(
        self,
        taxon_key: Optional[int] = None,
        taxon_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        state_province: Optional[str] = None,
        locality: Optional[str] = None,
        force_api: Optional[Literal["auto", "artportalen", "gbif"]] = None  # Not used for DB queries
    ) -> Dict[str, Any]:
        """Search for occurrences matching the given criteria.
        
        Args:
            taxon_key: GBIF taxon key (not directly supported - database stores species names)
            taxon_id: Artportalen taxon ID (not directly supported - database stores species names)
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)
            country: ISO country code (filtered by api_source, default SE for Artportalen)
            limit: Maximum number of results to return
            offset: Number of results to skip for pagination
            state_province: State or province filter (matches location_name)
            locality: Locality filter (matches location_name)
            force_api: Not used for database queries (for API compatibility only)
            
        Returns:
            Dictionary with 'results' list and 'count' matching API format
        """
        try:
            # Build WHERE clause
            conditions = []
            params = []
            
            if start_date:
                conditions.append("observation_date >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("observation_date <= ?")
                params.append(end_date)
            
            # Note: taxon_key and taxon_id are not directly filterable in database
            # Database stores species_name and species_scientific instead
            # This limitation could be addressed with a taxon lookup table in the future
            if taxon_key or taxon_id:
                logger.debug(f"taxon_key/taxon_id filtering not supported in database (stored as species names)")
            
            # Filter by country (default to SE for Artportalen data)
            if country:
                # Database stores api_source, not country directly
                # For now, assume Artportalen data is from Sweden (SE)
                # Future enhancement: add country column to schema
                if country.upper() != "SE":
                    logger.debug(f"Country filtering limited - database primarily contains SE data")
            
            # Filter by state/province (matches location_name)
            if state_province:
                conditions.append("(location_name LIKE ? OR location_name LIKE ?)")
                params.append(f"%{state_province}%")
                params.append(f"%{state_province.capitalize()}%")
            
            # Filter by locality (matches location_name)
            if locality:
                conditions.append("location_name LIKE ?")
                params.append(f"%{locality}%")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get total count
            count_sql = f"SELECT COUNT(*) FROM observations WHERE {where_clause}"
            total_result = self.connection.execute(count_sql, params).fetchone()
            total = total_result[0] if total_result else 0
            
            # Build query with pagination
            query_sql = f"""
                SELECT 
                    id, observation_date, species_name, species_scientific,
                    latitude, longitude, location_name, observer_name,
                    quantity, verification_status, habitat, coordinate_uncertainty,
                    api_source, created_at, updated_at
                FROM observations
                WHERE {where_clause}
                ORDER BY observation_date DESC
            """
            
            if limit:
                query_sql += f" LIMIT {limit}"
                if offset:
                    query_sql += f" OFFSET {offset}"
            
            # Execute query
            results = self.connection.execute(query_sql, params).fetchall()
            
            # Convert to normalized format matching API responses
            records = []
            for row in results:
                # Convert database record to API-like format
                db_record = {
                    "id": row[0],
                    "observation_date": row[1],
                    "species_name": row[2],
                    "species_scientific": row[3],
                    "latitude": row[4],
                    "longitude": row[5],
                    "location_name": row[6],
                    "observer_name": row[7],
                    "quantity": row[8],
                    "verification_status": row[9],
                    "habitat": row[10],
                    "coordinate_uncertainty": row[11],
                    "api_source": row[12],
                }
                
                # Transform to API response format
                normalized_record = self._db_record_to_api_format(db_record)
                records.append(normalized_record)
            
            logger.info(f"Query returned {len(records)} results (total: {total})")
            
            return {
                "results": records,
                "count": total,
                "_api_source": "database"
            }
            
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return {
                "results": [],
                "count": 0,
                "_api_source": "database",
                "error": str(e)
            }
    
    def _db_record_to_api_format(self, db_record: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database record to API response format.
        
        Args:
            db_record: Database record dictionary
            
        Returns:
            Normalized record matching API response format
        """
        # Create a record in API-like format for normalization
        api_like_record = {
            "occurrenceId": db_record.get("id"),
            "event": {},
            "taxon": {
                "scientificName": db_record.get("species_scientific"),
                "vernacularName": db_record.get("species_name"),
            },
            "location": {
                "decimalLatitude": db_record.get("latitude"),
                "decimalLongitude": db_record.get("longitude"),
            },
            "occurrence": {
                "individualCount": db_record.get("quantity"),
                "occurrenceId": db_record.get("id"),
            },
            "identification": {},
            "countryCode": "SE",  # Default for Artportalen data
        }
        
        # Add date if available
        if db_record.get("observation_date"):
            date_str = db_record.get("observation_date")
            if isinstance(date_str, date):
                date_str = date_str.isoformat()
            api_like_record["event"]["startDate"] = date_str
            api_like_record["event"]["endDate"] = date_str
        
        # Add coordinate uncertainty if available
        if db_record.get("coordinate_uncertainty") is not None:
            api_like_record["location"]["coordinateUncertaintyInMeters"] = db_record.get("coordinate_uncertainty")
        
        # Add verification status if available
        verification_status = db_record.get("verification_status")
        if verification_status:
            api_like_record["identification"]["verified"] = verification_status == "verified"
            api_like_record["identification"]["uncertainIdentification"] = verification_status == "uncertain"
        
        # Add location name if available
        if db_record.get("location_name"):
            api_like_record["location"]["site"] = {"name": db_record.get("location_name")}
        
        # Add observer if available
        if db_record.get("observer_name"):
            api_like_record["recordedBy"] = db_record.get("observer_name")
        
        # Normalize using existing adapter
        normalized = normalize_artportalen_record(api_like_record)
        
        # Ensure data source indicator
        normalized["_api_source"] = "database"
        
        return normalized

