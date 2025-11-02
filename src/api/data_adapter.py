"""Data adapter to normalize Artportalen API responses to GBIF format."""
from typing import Dict, List, Any, Optional
from datetime import datetime, date


def normalize_artportalen_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an Artportalen observation record to match GBIF format.

    Args:
        record: Raw Artportalen observation record

    Returns:
        Normalized record matching GBIF format
    """
    normalized = {}

    # Map common fields
    # Date handling
    event_date = None
    if "startDate" in record:
        event_date = record["startDate"]
    elif "observationDate" in record:
        event_date = record["observationDate"]
    elif "date" in record:
        event_date = record["date"]
    elif "eventDate" in record:
        event_date = record["eventDate"]

    if event_date:
        # Parse date string if needed
        if isinstance(event_date, str):
            try:
                # Try various date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"]:
                    try:
                        parsed_date = datetime.strptime(event_date.split('T')[0], "%Y-%m-%d")
                        normalized["eventDate"] = parsed_date.strftime("%Y-%m-%d")
                        normalized["year"] = parsed_date.year
                        normalized["month"] = parsed_date.month
                        normalized["day"] = parsed_date.day
                        break
                    except:
                        continue
            except:
                normalized["eventDate"] = event_date
        else:
            normalized["eventDate"] = str(event_date)

    # Scientific name
    scientific_name = None
    if "scientificName" in record:
        scientific_name = record["scientificName"]
    elif "scientificname" in record:
        scientific_name = record["scientificname"]
    elif "taxon" in record and isinstance(record["taxon"], dict):
        scientific_name = record["taxon"].get("scientificName") or record["taxon"].get("scientificname")
    
    if scientific_name:
        normalized["scientificName"] = scientific_name
        normalized["species"] = scientific_name

    # Vernacular/common name
    vernacular_name = None
    if "vernacularName" in record:
        vernacular_name = record["vernacularName"]
    elif "vernacularname" in record:
        vernacular_name = record["vernacularname"]
    elif "commonName" in record:
        vernacular_name = record["commonName"]
    elif "commonname" in record:
        vernacular_name = record["commonname"]
    elif "taxon" in record and isinstance(record["taxon"], dict):
        vernacular_name = record["taxon"].get("vernacularName") or record["taxon"].get("vernacularname") or record["taxon"].get("commonName")
    
    if vernacular_name:
        normalized["vernacularName"] = vernacular_name

    # Location fields
    if "locality" in record:
        normalized["locality"] = record["locality"]
    elif "location" in record and isinstance(record["location"], dict):
        normalized["locality"] = record["location"].get("locality") or record["location"].get("name")

    if "stateProvince" in record:
        normalized["stateProvince"] = record["stateProvince"]
    elif "province" in record:
        normalized["stateProvince"] = record["province"]
    elif "stateprovince" in record:
        normalized["stateProvince"] = record["stateprovince"]
    elif "location" in record and isinstance(record["location"], dict):
        normalized["stateProvince"] = record["location"].get("stateProvince") or record["location"].get("province")

    if "countryCode" in record:
        normalized["countryCode"] = record["countryCode"]
    elif "country" in record:
        country = record["country"]
        if isinstance(country, str) and len(country) == 2:
            normalized["countryCode"] = country.upper()
        elif isinstance(country, dict):
            normalized["countryCode"] = country.get("code", country.get("countryCode", "SE"))

    # Coordinates
    latitude = None
    longitude = None

    if "decimalLatitude" in record:
        latitude = record["decimalLatitude"]
    elif "latitude" in record:
        latitude = record["latitude"]
    elif "coordinates" in record and isinstance(record["coordinates"], dict):
        latitude = record["coordinates"].get("latitude") or record["coordinates"].get("lat")
        longitude = record["coordinates"].get("longitude") or record["coordinates"].get("lon") or record["coordinates"].get("lng")
    elif "location" in record and isinstance(record["location"], dict):
        coords = record["location"].get("coordinates") or record["location"]
        if isinstance(coords, dict):
            latitude = coords.get("latitude") or coords.get("lat")
            longitude = coords.get("longitude") or coords.get("lon") or coords.get("lng")
        elif isinstance(coords, list) and len(coords) >= 2:
            # GeoJSON format: [longitude, latitude]
            longitude = coords[0]
            latitude = coords[1]

    if "decimalLongitude" in record:
        longitude = record["decimalLongitude"]
    elif "longitude" in record:
        longitude = record["longitude"]

    if latitude is not None:
        try:
            normalized["decimalLatitude"] = float(latitude)
        except (ValueError, TypeError):
            pass

    if longitude is not None:
        try:
            normalized["decimalLongitude"] = float(longitude)
        except (ValueError, TypeError):
            pass

    # Observer/recorder
    if "recordedBy" in record:
        normalized["recordedBy"] = record["recordedBy"]
    elif "observer" in record:
        normalized["recordedBy"] = record["observer"]
    elif "recorder" in record:
        normalized["recordedBy"] = record["recorder"]
    elif "reportedBy" in record:
        normalized["recordedBy"] = record["reportedBy"]

    # Individual count
    if "individualCount" in record:
        normalized["individualCount"] = record["individualCount"]
    elif "count" in record:
        normalized["individualCount"] = record["count"]
    elif "quantity" in record:
        normalized["individualCount"] = record["quantity"]

    # Basis of record
    if "basisOfRecord" in record:
        normalized["basisOfRecord"] = record["basisOfRecord"]
    elif "basisofrecord" in record:
        normalized["basisOfRecord"] = record["basisofrecord"]
    else:
        normalized["basisOfRecord"] = "HUMAN_OBSERVATION"  # Default for Artportalen

    # Keep original record ID if available
    if "id" in record:
        normalized["id"] = record["id"]
    elif "sightingId" in record:
        normalized["id"] = record["sightingId"]
    elif "observationId" in record:
        normalized["id"] = record["observationId"]

    # Add source indicator
    normalized["_source"] = "artportalen"

    return normalized


def normalize_artportalen_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an Artportalen API response to match GBIF format.

    Args:
        response: Raw Artportalen API response

    Returns:
        Normalized response matching GBIF format
    """
    if "error" in response:
        return response

    normalized_response = {
        "results": [],
        "count": response.get("count", 0)
    }

    # Normalize each record
    results = response.get("results", [])
    if not results and "raw" in response:
        # Try to extract results from raw data
        raw = response["raw"]
        if isinstance(raw, list):
            results = raw
        elif isinstance(raw, dict):
            # Try common keys
            for key in ["items", "sightings", "observations", "data"]:
                if key in raw:
                    results = raw[key] if isinstance(raw[key], list) else []
                    break

    normalized_response["results"] = [
        normalize_artportalen_record(record) for record in results
    ]

    # Update count if we have results
    if normalized_response["results"] and normalized_response["count"] == 0:
        normalized_response["count"] = len(normalized_response["results"])

    # Preserve any metadata
    if "raw" in response:
        normalized_response["_raw"] = response["raw"]

    return normalized_response

