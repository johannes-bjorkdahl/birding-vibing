"""Data ingestion pipeline for loading observation data into DuckDB.

Provides batch processing, progress tracking, error handling,
and incremental update capabilities.
"""

import logging
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def transform_artportalen_to_db_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform an Artportalen API record to database schema format.
    
    Args:
        record: Raw Artportalen observation record (can be normalized or raw)
        
    Returns:
        Dictionary with database record fields, or None if transformation fails
    """
    try:
        db_record = {}
        
        # Extract observation ID
        # Artportalen uses occurrence.occurrenceId (nested in occurrence object)
        occurrence_id = None
        if "occurrence" in record and isinstance(record["occurrence"], dict):
            occurrence_id = record["occurrence"].get("occurrenceId")
        
        db_record["id"] = (
            occurrence_id or
            record.get("occurrenceId") or  # Top-level fallback
            record.get("id") or
            record.get("observationId") or
            f"artportalen_{hash(str(record))}"  # Fallback: generate ID from record hash
        )
        
        # Extract observation date
        observation_date = None
        if "event" in record and isinstance(record["event"], dict):
            observation_date = record["event"].get("startDate") or record["event"].get("endDate")
        elif "eventDate" in record:
            observation_date = record["eventDate"]
        elif "observationDate" in record:
            observation_date = record["observationDate"]
        elif "startDate" in record:
            observation_date = record["startDate"]
        elif "date" in record:
            observation_date = record["date"]
        
        if observation_date:
            # Parse date string to date object
            if isinstance(observation_date, str):
                try:
                    # Extract date part (before T and timezone)
                    date_str = observation_date.split('T')[0].split('+')[0]
                    db_record["observation_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    try:
                        db_record["observation_date"] = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    except Exception:
                        logger.warning(f"Could not parse date: {observation_date}")
                        return None
            elif isinstance(observation_date, date):
                db_record["observation_date"] = observation_date
            elif isinstance(observation_date, datetime):
                db_record["observation_date"] = observation_date.date()
        else:
            logger.warning("No observation date found in record")
            return None
        
        # Extract species information
        species_name = None
        species_scientific = None
        
        if "taxon" in record and isinstance(record["taxon"], dict):
            taxon = record["taxon"]
            species_name = taxon.get("vernacularName") or taxon.get("commonName")
            species_scientific = taxon.get("scientificName")
        elif "vernacularName" in record:
            species_name = record["vernacularName"]
            species_scientific = record.get("scientificName")
        elif "commonName" in record:
            species_name = record["commonName"]
            species_scientific = record.get("scientificName")
        
        db_record["species_name"] = species_name
        db_record["species_scientific"] = species_scientific
        
        # Extract location information
        latitude = None
        longitude = None
        
        if "location" in record and isinstance(record["location"], dict):
            location = record["location"]
            latitude = location.get("decimalLatitude") or location.get("latitude")
            longitude = location.get("decimalLongitude") or location.get("longitude")
            # Extract location name
            location_name = (
                location.get("site", {}).get("name") if isinstance(location.get("site"), dict)
                else location.get("locationName") or
                location.get("siteName") or
                location.get("name")
            )
            db_record["location_name"] = location_name
        else:
            latitude = record.get("decimalLatitude") or record.get("latitude")
            longitude = record.get("decimalLongitude") or record.get("longitude")
            db_record["location_name"] = (
                record.get("locationName") or
                record.get("siteName") or
                record.get("locality")
            )
        
        # Validate coordinates
        try:
            db_record["latitude"] = float(latitude) if latitude is not None else None
            db_record["longitude"] = float(longitude) if longitude is not None else None
        except (ValueError, TypeError):
            logger.warning(f"Invalid coordinates in record: lat={latitude}, lon={longitude}")
            return None
        
        if db_record["latitude"] is None or db_record["longitude"] is None:
            logger.warning("Missing required coordinates")
            return None
        
        # Extract observer information
        if "owner" in record:
            owner = record["owner"]
            if isinstance(owner, dict):
                db_record["observer_name"] = owner.get("name") or owner.get("userName")
            else:
                db_record["observer_name"] = str(owner)
        else:
            db_record["observer_name"] = record.get("observerName") or record.get("observer")
        
        # Extract quantity
        quantity = None
        if "occurrence" in record and isinstance(record["occurrence"], dict):
            quantity = record["occurrence"].get("individualCount")
        else:
            quantity = record.get("individualCount") or record.get("quantity") or record.get("count")
        
        try:
            db_record["quantity"] = int(quantity) if quantity is not None else None
        except (ValueError, TypeError):
            db_record["quantity"] = None
        
        # Extract verification status
        verification_status = None
        if "identification" in record and isinstance(record["identification"], dict):
            identification = record["identification"]
            if identification.get("verified"):
                verification_status = "verified"
            elif identification.get("uncertainIdentification"):
                verification_status = "uncertain"
            else:
                verification_status = "unverified"
        else:
            verification_status = record.get("verificationStatus") or record.get("status")
        
        db_record["verification_status"] = verification_status
        
        # Extract habitat (if available)
        db_record["habitat"] = (
            record.get("habitat") or
            record.get("biotope") or
            record.get("environment")
        )
        
        # Extract coordinate uncertainty
        uncertainty = None
        if "location" in record and isinstance(record["location"], dict):
            uncertainty = record["location"].get("coordinateUncertaintyInMeters")
        else:
            uncertainty = record.get("coordinateUncertaintyInMeters") or record.get("uncertainty")
        
        try:
            db_record["coordinate_uncertainty"] = float(uncertainty) if uncertainty is not None else None
        except (ValueError, TypeError):
            db_record["coordinate_uncertainty"] = None
        
        # Set API source
        db_record["api_source"] = "artportalen"
        
        return db_record
        
    except Exception as e:
        logger.error(f"Failed to transform record: {e}")
        return None


class IngestionPipeline:
    """Pipeline for ingesting observation data into DuckDB.
    
    Handles batch processing, progress tracking, error handling,
    and incremental updates.
    
    Attributes:
        connection: DuckDB connection instance
        batch_size: Number of records to process per batch
        max_retries: Maximum number of retry attempts for failed batches
        retry_delay: Delay in seconds between retries
        rate_limit_delay: Delay in seconds between API calls (for rate limiting)
    """
    
    def __init__(
        self,
        connection,
        batch_size: int = 1000,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit_delay: float = 0.5
    ):
        """Initialize the ingestion pipeline.
        
        Args:
            connection: DuckDB connection instance
            batch_size: Number of records to process per batch
            max_retries: Maximum number of retry attempts for failed batches
            retry_delay: Delay in seconds between retries
            rate_limit_delay: Delay in seconds between API calls (for rate limiting)
        """
        self.connection = connection
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.total_ingested = 0
        self.total_failed = 0
        logger.info(f"Ingestion pipeline initialized with batch_size={batch_size}")
    
    def ingest_batch(self, records: List[Dict[str, Any]], retry_count: int = 0) -> bool:
        """Ingest a batch of observation records with retry logic.
        
        Args:
            records: List of observation records to insert
            retry_count: Current retry attempt number (internal use)
            
        Returns:
            True if ingestion succeeded, False otherwise
        """
        if not records:
            return True
        
        try:
            # Prepare insert statement with ON CONFLICT handling for upserts
            insert_sql = """
                INSERT INTO observations (
                    id, observation_date, species_name, species_scientific,
                    latitude, longitude, location_name, observer_name,
                    quantity, verification_status, habitat, coordinate_uncertainty,
                    api_source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    observation_date = EXCLUDED.observation_date,
                    species_name = EXCLUDED.species_name,
                    species_scientific = EXCLUDED.species_scientific,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    location_name = EXCLUDED.location_name,
                    observer_name = EXCLUDED.observer_name,
                    quantity = EXCLUDED.quantity,
                    verification_status = EXCLUDED.verification_status,
                    habitat = EXCLUDED.habitat,
                    coordinate_uncertainty = EXCLUDED.coordinate_uncertainty,
                    api_source = EXCLUDED.api_source,
                    updated_at = EXCLUDED.updated_at
            """
            
            # Prepare data tuples
            data_tuples = []
            now = datetime.now()
            for record in records:
                data_tuples.append((
                    record.get("id"),
                    record.get("observation_date"),
                    record.get("species_name"),
                    record.get("species_scientific"),
                    record.get("latitude"),
                    record.get("longitude"),
                    record.get("location_name"),
                    record.get("observer_name"),
                    record.get("quantity"),
                    record.get("verification_status"),
                    record.get("habitat"),
                    record.get("coordinate_uncertainty"),
                    record.get("api_source"),
                    now,
                    now,
                ))
            
            # Execute batch insert
            self.connection.executemany(insert_sql, data_tuples)
            self.connection.commit()
            
            self.total_ingested += len(records)
            logger.info(f"Successfully ingested {len(records)} records (total: {self.total_ingested})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest batch (attempt {retry_count + 1}/{self.max_retries + 1}): {e}")
            try:
                self.connection.rollback()
            except Exception:
                pass  # Rollback may fail if connection is in bad state
            
            # Retry logic
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay * (retry_count + 1))  # Exponential backoff
                return self.ingest_batch(records, retry_count + 1)
            
            self.total_failed += len(records)
            return False
    
    def check_existing_data(self, start_date: datetime, end_date: datetime) -> bool:
        """Check if data already exists for a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            True if data exists for this range, False otherwise
        """
        try:
            result = self.connection.execute(
                """
                SELECT COUNT(*) FROM observations
                WHERE observation_date >= ? AND observation_date <= ?
                """,
                [start_date.date(), end_date.date()]
            ).fetchone()
            
            return result[0] > 0 if result else False
            
        except Exception as e:
            logger.error(f"Failed to check existing data: {e}")
            return False
    
    def get_date_chunks(self, start_date: datetime, end_date: datetime) -> List[tuple]:
        """Generate monthly date chunks for batch processing.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of (start, end) date tuples for each month
        """
        chunks = []
        current = start_date
        
        while current < end_date:
            # Calculate end of current month
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1, day=1)
            else:
                next_month = current.replace(month=current.month + 1, day=1)
            
            chunk_end = min(next_month - timedelta(days=1), end_date)
            chunks.append((current, chunk_end))
            
            current = next_month
        
        return chunks
    
    def split_date_range_into_weeks(self, start_date: datetime, end_date: datetime) -> List[tuple]:
        """Split a date range into weekly chunks.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of (start, end) date tuples for each week
        """
        chunks = []
        current = start_date
        
        while current < end_date:
            # Calculate end of current week (7 days)
            week_end = min(current + timedelta(days=6), end_date)
            chunks.append((current, week_end))
            
            # Move to next week
            current = week_end + timedelta(days=1)
        
        return chunks
    
    def split_date_range_into_biweeks(self, start_date: datetime, end_date: datetime) -> List[tuple]:
        """Split a date range into bi-weekly chunks (2 weeks).
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of (start, end) date tuples for each bi-week period
        """
        chunks = []
        current = start_date
        
        while current < end_date:
            # Calculate end of current bi-week (14 days)
            biweek_end = min(current + timedelta(days=13), end_date)
            chunks.append((current, biweek_end))
            
            # Move to next bi-week
            current = biweek_end + timedelta(days=1)
        
        return chunks
    
    def split_date_range_into_days(self, start_date: datetime, end_date: datetime) -> List[tuple]:
        """Split a date range into daily chunks.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of (start, end) date tuples for each day
        """
        chunks = []
        current = start_date
        
        while current <= end_date:
            chunk_end = min(current.replace(hour=23, minute=59, second=59), end_date)
            chunks.append((current, chunk_end))
            
            # Move to next day
            current = (chunk_end + timedelta(seconds=1)).replace(hour=0, minute=0, second=0)
        
        return chunks
    
    def process_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        fetch_function: Callable[[date, date, int, int], Dict[str, Any]],
        skip_existing: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_records: Optional[int] = None,
        auto_split_large_chunks: bool = True
    ) -> Dict[str, Any]:
        """Process a date range by fetching and ingesting data in monthly chunks.
        
        Args:
            start_date: Start date for processing
            end_date: End date for processing
            fetch_function: Function that takes (start_date, end_date, offset, limit) and returns API response
            skip_existing: If True, skip date ranges that already have data
            progress_callback: Optional callback function(current, total, message) for progress updates
            max_records: Optional limit on number of records to fetch per month (for testing)
            auto_split_large_chunks: If True, automatically split months exceeding 10,000 records into smaller chunks
            
        Returns:
            Dictionary with processing results:
            - success: bool - True if processing completed successfully
            - total_chunks: int - Total number of chunks processed
            - processed_chunks: int - Number of chunks successfully processed
            - skipped_chunks: int - Number of chunks skipped (already had data)
            - total_ingested: int - Total records ingested
            - total_failed: int - Total records that failed ingestion
        """
        # Get initial monthly chunks
        monthly_chunks = self.get_date_chunks(start_date, end_date)
        
        # Expand chunks if auto-splitting is enabled and chunks might exceed limits
        # Use recursive splitting to ensure all chunks are under 10,000 records
        def recursive_split_chunk(chunk_start: datetime, chunk_end: datetime, max_records: int = 10000) -> List[tuple]:
            """Recursively split a chunk until all sub-chunks are under max_records."""
            # Check if data already exists
            if skip_existing and self.check_existing_data(chunk_start, chunk_end):
                return [(chunk_start, chunk_end, "skip")]
            
            # Check total count for this chunk
            if auto_split_large_chunks:
                try:
                    test_response = fetch_function(chunk_start.date(), chunk_end.date(), 0, 1000)
                    total_count = test_response.get("count") or test_response.get("totalCount", 0)
                    
                    # If chunk exceeds limit, split it further
                    if total_count > max_records:
                        # Calculate chunk duration
                        duration = (chunk_end - chunk_start).days + 1
                        
                        if duration > 7:
                            # Split into weekly chunks
                            logger.info(
                                f"Chunk {chunk_start.date()} to {chunk_end.date()} has {total_count} records, "
                                f"exceeding API limit. Splitting into weekly chunks..."
                            )
                            weekly_chunks = self.split_date_range_into_weeks(chunk_start, chunk_end)
                            result = []
                            for week_start, week_end in weekly_chunks:
                                result.extend(recursive_split_chunk(week_start, week_end, max_records))
                            return result
                        elif duration > 1:
                            # Split into daily chunks
                            logger.info(
                                f"Chunk {chunk_start.date()} to {chunk_end.date()} has {total_count} records, "
                                f"exceeding API limit. Splitting into daily chunks..."
                            )
                            daily_chunks = self.split_date_range_into_days(chunk_start, chunk_end)
                            result = []
                            for day_start, day_end in daily_chunks:
                                result.extend(recursive_split_chunk(day_start, day_end, max_records))
                            return result
                        else:
                            # Single day exceeds limit - cannot split further
                            # Will fetch up to 10,000 records with a warning
                            logger.warning(
                                f"Single day {chunk_start.date()} has {total_count} records, "
                                f"exceeding API limit. Will fetch maximum {max_records} records."
                            )
                            return [(chunk_start, chunk_end, "process")]
                except Exception as e:
                    logger.warning(f"Could not check total count for {chunk_start.date()}, proceeding with chunk: {e}")
            
            # Chunk is small enough or auto-split is disabled
            return [(chunk_start, chunk_end, "process")]
        
        all_chunks = []
        for chunk_start, chunk_end in monthly_chunks:
            all_chunks.extend(recursive_split_chunk(chunk_start, chunk_end))
        
        total_chunks = len(all_chunks)
        processed_chunks = 0
        skipped_chunks = 0
        
        logger.info(f"Processing {total_chunks} chunks from {start_date.date()} to {end_date.date()}")
        
        for chunk_start, chunk_end, chunk_type in all_chunks:
            # Handle skip chunks (already checked for existing data)
            if chunk_type == "skip":
                logger.info(f"Skipping existing data for {chunk_start.date()} to {chunk_end.date()}")
                skipped_chunks += 1
                processed_chunks += 1
                if progress_callback:
                    progress_callback(processed_chunks, total_chunks, f"⏭️ Skipped (already exists): {chunk_start.date()} to {chunk_end.date()}")
                continue
            
            # Fetch data for this chunk
            try:
                if progress_callback:
                    progress_callback(
                        processed_chunks,
                        total_chunks,
                        f"Fetching: {chunk_start.date()} to {chunk_end.date()}"
                    )
                
                # Fetch all records with pagination
                # API limits (per official docs):
                # - Maximum page size: 1000 records per request (CANNOT request more)
                # - Maximum total: 10,000 records per search query (skip + take cannot exceed 10,000)
                # So we MUST paginate: 1000 per request, up to 10 requests maximum
                # Source: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/FAQ.md
                all_records = []
                offset = 0
                limit = 1000  # API max page size per request (cannot be higher - this is the limit!)
                max_total_records = 10000  # API max total per search query
                total_count = None
                
                while True:
                    # Check if we're approaching the API's 10,000 record limit
                    if offset + limit > max_total_records:
                        logger.warning(
                            f"Reached API limit of {max_total_records} records per search query. "
                            f"Fetched {len(all_records)} records for {chunk_start.date()} to {chunk_end.date()}. "
                            f"Consider breaking date range into smaller chunks or using export endpoints."
                        )
                        break
                    
                    # Update progress during pagination
                    if progress_callback:
                        progress_callback(
                            processed_chunks,
                            total_chunks,
                            f"Fetching page {offset // limit + 1} ({len(all_records)} records so far)..."
                        )
                    
                    # Fetch a page of results
                    try:
                        response = fetch_function(chunk_start.date(), chunk_end.date(), offset, limit)
                        
                        # Check for API errors
                        if "error" in response:
                            error_msg = response.get("error", "Unknown error")
                            logger.error(f"API error during fetch: {error_msg}")
                            raise Exception(f"API returned error: {error_msg}")
                    except Exception as fetch_error:
                        logger.error(f"Failed to fetch page at offset {offset}: {fetch_error}")
                        # If it's the first page, fail the whole chunk
                        if offset == 0:
                            raise
                        # Otherwise, log and break (we got some data)
                        logger.warning(f"Stopping pagination due to error after fetching {len(all_records)} records")
                        break
                    
                    # Extract records from response
                    records = response.get("results", [])
                    
                    # Get total count from first response
                    if total_count is None:
                        total_count = response.get("count") or response.get("totalCount", 0)
                        if total_count > max_total_records:
                            logger.warning(
                                f"Total available records ({total_count}) exceeds API limit ({max_total_records}). "
                                f"Will only fetch first {max_total_records} records."
                            )
                    
                    # Apply max_records limit if specified (for testing)
                    if max_records is not None:
                        remaining = max_records - len(all_records)
                        if remaining <= 0:
                            logger.info(f"Reached max_records limit ({max_records}), stopping pagination")
                            break
                        records = records[:remaining]
                    
                    all_records.extend(records)
                    
                    # Check if we've fetched all records
                    if not records or len(records) < limit:
                        break
                    
                    # Stop if we've reached max_records limit
                    if max_records is not None and len(all_records) >= max_records:
                        logger.info(f"Reached max_records limit ({max_records}), stopping pagination")
                        break
                    
                    # Stop if we've hit the API's total limit
                    if len(all_records) >= max_total_records:
                        logger.warning(f"Reached API total limit of {max_total_records} records")
                        break
                    
                    offset += len(records)
                    
                    # Minimal rate limiting delay - only if we're not hitting errors
                    # Reduced from 2.0s to 0.5s since we have retry logic for 429 errors
                    if self.rate_limit_delay > 0 and len(records) > 0:
                        time.sleep(min(self.rate_limit_delay, 0.5))  # Cap at 0.5s max
                
                if not all_records:
                    logger.info(f"No records found for {chunk_start.date()} to {chunk_end.date()}")
                    processed_chunks += 1
                    continue
                
                logger.info(f"Fetched {len(all_records)} records (total available: {total_count}) for {chunk_start.date()} to {chunk_end.date()}")
                
                # Transform records to database format
                db_records = []
                for record in all_records:
                    db_record = transform_artportalen_to_db_record(record)
                    if db_record:  # Only add if transformation succeeded
                        db_records.append(db_record)
                
                # Ingest in batches
                for i in range(0, len(db_records), self.batch_size):
                    batch = db_records[i:i + self.batch_size]
                    self.ingest_batch(batch)
                
                processed_chunks += 1
                
                if progress_callback:
                    progress_callback(
                        processed_chunks,
                        total_chunks,
                        f"Processed: {chunk_start.date()} ({len(db_records)} records)"
                    )
                
                # Rate limiting delay
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)
                    
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk_start.date()} to {chunk_end.date()}: {e}", exc_info=True)
                if progress_callback:
                    progress_callback(
                        processed_chunks + 1,
                        total_chunks,
                        f"❌ Failed: {chunk_start.date()} to {chunk_end.date()} - {str(e)[:100]}"
                    )
                processed_chunks += 1
                self.total_failed += 1
                continue
        
        # Log completion statistics
        logger.info(
            f"Processing complete: {processed_chunks}/{total_chunks} chunks processed, "
            f"{skipped_chunks} skipped, {self.total_ingested} records ingested, "
            f"{self.total_failed} failed"
        )
        
        # Return True if most chunks succeeded (at least 80% or all skipped)
        success_rate = (processed_chunks - skipped_chunks) / max(total_chunks - skipped_chunks, 1) if total_chunks > skipped_chunks else 1.0
        success = success_rate >= 0.8 or skipped_chunks == total_chunks
        
        # Return both success status and statistics for compatibility
        return {
            "success": success,
            "total_chunks": total_chunks,
            "processed_chunks": processed_chunks,
            "skipped_chunks": skipped_chunks,
            "total_ingested": self.total_ingested,
            "total_failed": self.total_failed
        }
    
    def reset_stats(self):
        """Reset ingestion statistics."""
        self.total_ingested = 0
        self.total_failed = 0

