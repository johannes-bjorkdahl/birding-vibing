#!/usr/bin/env python3
"""Data validation script for DuckDB observations database.

Validates data quality, completeness, and integrity of the observations database.
Checks for duplicates, invalid coordinates, missing required fields, and other issues.

Usage:
    python scripts/validate_data.py [--db-path PATH] [--verbose] [--fix]
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DuckDBConnection
from src.database.schema import validate_schema, get_schema_version, SCHEMA_VERSION
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Validates data quality in the observations database."""
    
    def __init__(self, db_path: Path):
        """Initialize validator with database path.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.connection = None
        self.issues: List[Dict] = []
        self.stats: Dict = {}
        
    def __enter__(self):
        """Context manager entry."""
        try:
            self.connection = DuckDBConnection(self.db_path)
        except Exception as e:
            error_msg = str(e)
            if "Conflicting lock" in error_msg or "lock" in error_msg.lower():
                logger.error(
                    "Database is locked. The Streamlit app or another process is using the database.\n"
                    "Please stop the Streamlit app before running validation:\n"
                    "  1. Stop the Streamlit app (Ctrl+C or close the terminal)\n"
                    "  2. Wait a few seconds for the lock to release\n"
                    "  3. Run validation again"
                )
                raise RuntimeError(
                    "Database is locked. Please stop the Streamlit app before running validation."
                ) from e
            raise
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.connection:
            self.connection.close()
    
    def validate_schema(self) -> bool:
        """Validate database schema.
        
        Returns:
            True if schema is valid, False otherwise
        """
        logger.info("Validating schema...")
        
        if not validate_schema(self.connection.connection):
            self.issues.append({
                'type': 'schema',
                'severity': 'error',
                'message': 'Schema validation failed'
            })
            return False
        
        version = get_schema_version(self.connection.connection)
        logger.info(f"✓ Schema version: {version}")
        return True
    
    def validate_data_completeness(self) -> Dict:
        """Check data completeness - required fields.
        
        Returns:
            Dictionary with completeness statistics
        """
        logger.info("Checking data completeness...")
        
        conn = self.connection.connection
        
        # Required fields that should not be NULL
        required_fields = [
            ('id', 'TEXT'),
            ('observation_date', 'DATE'),
            ('species_name', 'TEXT'),
            ('latitude', 'DOUBLE'),
            ('longitude', 'DOUBLE'),
            ('api_source', 'TEXT')
        ]
        
        completeness = {}
        total_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        
        if total_count == 0:
            logger.warning("⚠ No data in database")
            return {'total': 0, 'fields': {}}
        
        for field, field_type in required_fields:
            null_count = conn.execute(
                f"SELECT COUNT(*) FROM observations WHERE {field} IS NULL"
            ).fetchone()[0]
            
            completeness[field] = {
                'null_count': null_count,
                'null_percentage': (null_count / total_count * 100) if total_count > 0 else 0
            }
            
            if null_count > 0:
                self.issues.append({
                    'type': 'completeness',
                    'severity': 'error' if field in ['id', 'observation_date', 'species_name'] else 'warning',
                    'field': field,
                    'message': f'{null_count} records ({null_count/total_count*100:.2f}%) have NULL {field}'
                })
        
        logger.info(f"✓ Completeness check: {total_count} total records")
        return {'total': total_count, 'fields': completeness}
    
    def validate_coordinates(self) -> Dict:
        """Validate coordinate data.
        
        Returns:
            Dictionary with coordinate validation statistics
        """
        logger.info("Validating coordinates...")
        
        conn = self.connection.connection
        
        # Check for invalid coordinates
        invalid_coords = conn.execute("""
            SELECT COUNT(*) FROM observations
            WHERE latitude < -90 OR latitude > 90
               OR longitude < -180 OR longitude > 180
        """).fetchone()[0]
        
        # Check for coordinates in Sweden (rough bounds)
        sweden_bounds = {
            'lat_min': 55.0,
            'lat_max': 70.0,
            'lon_min': 10.0,
            'lon_max': 25.0
        }
        
        in_sweden = conn.execute("""
            SELECT COUNT(*) FROM observations
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
        """, [sweden_bounds['lat_min'], sweden_bounds['lat_max'],
              sweden_bounds['lon_min'], sweden_bounds['lon_max']]).fetchone()[0]
        
        total = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        
        if invalid_coords > 0:
            self.issues.append({
                'type': 'coordinates',
                'severity': 'error',
                'message': f'{invalid_coords} records have invalid coordinates (outside -90/90 or -180/180)'
            })
        
        if total > 0:
            sweden_percentage = (in_sweden / total * 100)
            if sweden_percentage < 50:
                self.issues.append({
                    'type': 'coordinates',
                    'severity': 'warning',
                    'message': f'Only {sweden_percentage:.1f}% of coordinates are within Sweden bounds'
                })
        
        logger.info(f"✓ Coordinate validation: {invalid_coords} invalid, {in_sweden}/{total} in Sweden")
        
        return {
            'invalid': invalid_coords,
            'in_sweden': in_sweden,
            'total': total
        }
    
    def validate_dates(self) -> Dict:
        """Validate date data.
        
        Returns:
            Dictionary with date validation statistics
        """
        logger.info("Validating dates...")
        
        conn = self.connection.connection
        
        # Check for future dates
        future_dates = conn.execute("""
            SELECT COUNT(*) FROM observations
            WHERE observation_date > CURRENT_DATE
        """).fetchone()[0]
        
        # Check for very old dates (before 1900)
        old_dates = conn.execute("""
            SELECT COUNT(*) FROM observations
            WHERE observation_date < DATE '1900-01-01'
        """).fetchone()[0]
        
        # Get date range
        date_range = conn.execute("""
            SELECT MIN(observation_date), MAX(observation_date)
            FROM observations
        """).fetchone()
        
        if future_dates > 0:
            self.issues.append({
                'type': 'dates',
                'severity': 'warning',
                'message': f'{future_dates} records have future dates'
            })
        
        if old_dates > 0:
            self.issues.append({
                'type': 'dates',
                'severity': 'warning',
                'message': f'{old_dates} records have dates before 1900'
            })
        
        logger.info(f"✓ Date validation: {future_dates} future, {old_dates} very old")
        logger.info(f"  Date range: {date_range[0]} to {date_range[1]}")
        
        return {
            'future_dates': future_dates,
            'old_dates': old_dates,
            'date_range': date_range
        }
    
    def validate_duplicates(self) -> Dict:
        """Check for duplicate records.
        
        Returns:
            Dictionary with duplicate statistics
        """
        logger.info("Checking for duplicates...")
        
        conn = self.connection.connection
        
        # Check for duplicate IDs (should be unique)
        duplicate_ids = conn.execute("""
            SELECT id, COUNT(*) as count
            FROM observations
            GROUP BY id
            HAVING COUNT(*) > 1
        """).fetchall()
        
        # Check for near-duplicates (same date, species, location)
        near_duplicates = conn.execute("""
            SELECT observation_date, species_name, latitude, longitude, COUNT(*) as count
            FROM observations
            GROUP BY observation_date, species_name, latitude, longitude
            HAVING COUNT(*) > 1
        """).fetchall()
        
        duplicate_count = len(duplicate_ids)
        near_duplicate_count = len(near_duplicates)
        
        if duplicate_count > 0:
            self.issues.append({
                'type': 'duplicates',
                'severity': 'error',
                'message': f'{duplicate_count} duplicate IDs found (should be unique)'
            })
        
        if near_duplicate_count > 0:
            total_near_dups = sum(count - 1 for _, _, _, _, count in near_duplicates)
            self.issues.append({
                'type': 'duplicates',
                'severity': 'info',
                'message': f'{near_duplicate_count} sets of near-duplicate records ({total_near_dups} total duplicates)'
            })
        
        logger.info(f"✓ Duplicate check: {duplicate_count} duplicate IDs, {near_duplicate_count} near-duplicate sets")
        
        return {
            'duplicate_ids': duplicate_count,
            'near_duplicates': near_duplicate_count,
            'duplicate_id_list': duplicate_ids
        }
    
    def validate_species_data(self) -> Dict:
        """Validate species name data.
        
        Returns:
            Dictionary with species validation statistics
        """
        logger.info("Validating species data...")
        
        conn = self.connection.connection
        
        # Check for empty species names
        empty_species = conn.execute("""
            SELECT COUNT(*) FROM observations
            WHERE species_name IS NULL OR TRIM(species_name) = ''
        """).fetchone()[0]
        
        # Count unique species
        unique_species = conn.execute("""
            SELECT COUNT(DISTINCT species_name) FROM observations
        """).fetchone()[0]
        
        # Get top species
        top_species = conn.execute("""
            SELECT species_name, COUNT(*) as count
            FROM observations
            GROUP BY species_name
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        if empty_species > 0:
            self.issues.append({
                'type': 'species',
                'severity': 'error',
                'message': f'{empty_species} records have empty species names'
            })
        
        logger.info(f"✓ Species validation: {unique_species} unique species")
        logger.info(f"  Top species: {top_species[0][0] if top_species else 'N/A'} ({top_species[0][1] if top_species else 0} records)")
        
        return {
            'empty_species': empty_species,
            'unique_species': unique_species,
            'top_species': top_species
        }
    
    def get_statistics(self) -> Dict:
        """Get overall database statistics.
        
        Returns:
            Dictionary with statistics
        """
        logger.info("Gathering statistics...")
        
        conn = self.connection.connection
        
        stats = {}
        
        # Total records
        stats['total_records'] = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        
        # Date range
        date_range = conn.execute("""
            SELECT MIN(observation_date), MAX(observation_date)
            FROM observations
        """).fetchone()
        stats['date_range'] = {
            'min': date_range[0],
            'max': date_range[1]
        }
        
        # API source distribution
        api_sources = conn.execute("""
            SELECT api_source, COUNT(*) as count
            FROM observations
            GROUP BY api_source
        """).fetchall()
        stats['api_sources'] = dict(api_sources)
        
        # Records per year
        records_per_year = conn.execute("""
            SELECT EXTRACT(YEAR FROM observation_date) as year, COUNT(*) as count
            FROM observations
            GROUP BY year
            ORDER BY year
        """).fetchall()
        stats['records_per_year'] = dict(records_per_year)
        
        # Geographic distribution
        coord_stats = conn.execute("""
            SELECT 
                MIN(latitude) as min_lat,
                MAX(latitude) as max_lat,
                MIN(longitude) as min_lon,
                MAX(longitude) as max_lon,
                AVG(latitude) as avg_lat,
                AVG(longitude) as avg_lon
            FROM observations
        """).fetchone()
        
        stats['geographic'] = {
            'lat_range': (coord_stats[0], coord_stats[1]),
            'lon_range': (coord_stats[2], coord_stats[3]),
            'center': (coord_stats[4], coord_stats[5])
        }
        
        return stats
    
    def run_all_validations(self) -> bool:
        """Run all validation checks.
        
        Returns:
            True if all validations passed, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Starting data validation")
        logger.info("=" * 60)
        
        # Schema validation
        if not self.validate_schema():
            logger.error("Schema validation failed - aborting")
            return False
        
        # Data completeness
        self.stats['completeness'] = self.validate_data_completeness()
        
        # Coordinates
        self.stats['coordinates'] = self.validate_coordinates()
        
        # Dates
        self.stats['dates'] = self.validate_dates()
        
        # Duplicates
        self.stats['duplicates'] = self.validate_duplicates()
        
        # Species
        self.stats['species'] = self.validate_species_data()
        
        # Overall statistics
        self.stats['overall'] = self.get_statistics()
        
        return True
    
    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 60)
        print("DATA VALIDATION REPORT")
        print("=" * 60)
        
        # Overall statistics
        if 'overall' in self.stats:
            stats = self.stats['overall']
            print(f"\n📊 Overall Statistics:")
            print(f"   Total records: {stats['total_records']:,}")
            if stats.get('date_range'):
                print(f"   Date range: {stats['date_range']['min']} to {stats['date_range']['max']}")
            if stats.get('api_sources'):
                print(f"   API sources: {', '.join(f'{k}: {v:,}' for k, v in stats['api_sources'].items())}")
        
        # Issues
        print(f"\n⚠️  Issues Found: {len(self.issues)}")
        
        if self.issues:
            errors = [i for i in self.issues if i['severity'] == 'error']
            warnings = [i for i in self.issues if i['severity'] == 'warning']
            infos = [i for i in self.issues if i['severity'] == 'info']
            
            if errors:
                print(f"\n   ❌ Errors ({len(errors)}):")
                for issue in errors:
                    print(f"      - {issue['message']}")
            
            if warnings:
                print(f"\n   ⚠️  Warnings ({len(warnings)}):")
                for issue in warnings:
                    print(f"      - {issue['message']}")
            
            if infos:
                print(f"\n   ℹ️  Info ({len(infos)}):")
                for issue in infos:
                    print(f"      - {issue['message']}")
        else:
            print("   ✓ No issues found!")
        
        print("\n" + "=" * 60)
        
        # Summary
        error_count = len([i for i in self.issues if i['severity'] == 'error'])
        if error_count == 0:
            print("✅ Validation PASSED (no errors)")
        else:
            print(f"❌ Validation FAILED ({error_count} errors)")
        
        print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate DuckDB observations database'
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=Config.DATABASE_PATH,
        help='Path to DuckDB database file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if database exists
    if not args.db_path.exists():
        logger.error(f"Database file not found: {args.db_path}")
        return 1
    
    # Run validation
    try:
        with DataValidator(args.db_path) as validator:
            success = validator.run_all_validations()
            validator.print_report()
            
            return 0 if success and len([i for i in validator.issues if i['severity'] == 'error']) == 0 else 1
            
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

