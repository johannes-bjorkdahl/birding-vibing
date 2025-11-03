"""Data adapter to normalize Artportalen API responses to GBIF format."""
from typing import Dict, List, Any, Optional
from datetime import datetime, date


def normalize_artportalen_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an Artportalen observation record to match GBIF format.
    
    Artportalen API structure:
    - event: {startDate, endDate}
    - taxon: {id, scientificName, vernacularName, attributes}
    - location: {decimalLatitude, decimalLongitude, county: {name}, municipality: {name}}
    - occurrence: {individualCount, occurrenceId, occurrenceStatus}
    - identification: {verified, uncertainIdentification}
    - datasetName

    Args:
        record: Raw Artportalen observation record

    Returns:
        Normalized record matching GBIF format
    """
    normalized = {}

    # ===== DATE HANDLING =====
    # Artportalen uses nested event.startDate and event.endDate
    event_date = None
    if "event" in record and isinstance(record["event"], dict):
        event_date = record["event"].get("startDate") or record["event"].get("endDate")
    elif "startDate" in record:
        event_date = record["startDate"]
    elif "observationDate" in record:
        event_date = record["observationDate"]
    elif "date" in record:
        event_date = record["date"]
    elif "eventDate" in record:
        event_date = record["eventDate"]

    if event_date:
        # Parse date string
        if isinstance(event_date, str):
            try:
                # Extract date part (before T and timezone)
                date_str = event_date.split('T')[0].split('+')[0].split('-')[0:3]
                if len(date_str) >= 3:
                    parsed_date = datetime.strptime('-'.join(date_str), "%Y-%m-%d")
                    normalized["eventDate"] = parsed_date.strftime("%Y-%m-%d")
                    normalized["year"] = parsed_date.year
                    normalized["month"] = parsed_date.month
                    normalized["day"] = parsed_date.day
            except Exception:
                normalized["eventDate"] = event_date.split('T')[0] if 'T' in event_date else event_date
        else:
            normalized["eventDate"] = str(event_date)

    # ===== TAXON/SPECIES INFORMATION =====
    # Artportalen uses nested taxon.scientificName and taxon.vernacularName
    scientific_name = None
    if "taxon" in record and isinstance(record["taxon"], dict):
        scientific_name = record["taxon"].get("scientificName")
        # Preserve full taxon object including attributes for bird filtering
        normalized["_taxon"] = record["taxon"]
    elif "scientificName" in record:
        scientific_name = record["scientificName"]
    elif "scientificname" in record:
        scientific_name = record["scientificname"]
    
    if scientific_name:
        normalized["scientificName"] = scientific_name
        normalized["species"] = scientific_name

    # Vernacular/common name
    vernacular_name = None
    if "taxon" in record and isinstance(record["taxon"], dict):
        vernacular_name = record["taxon"].get("vernacularName")
    elif "vernacularName" in record:
        vernacular_name = record["vernacularName"]
    elif "vernacularname" in record:
        vernacular_name = record["vernacularname"]
    elif "commonName" in record:
        vernacular_name = record["commonName"]
    elif "commonname" in record:
        vernacular_name = record["commonname"]
    
    if vernacular_name:
        normalized["vernacularName"] = vernacular_name

    # ===== LOCATION INFORMATION =====
    # Artportalen uses nested location object
    location = record.get("location", {})
    if isinstance(location, dict):
        # Coordinates - CRITICAL for map display
        if "decimalLatitude" in location:
            try:
                normalized["decimalLatitude"] = float(location["decimalLatitude"])
                normalized["latitude"] = float(location["decimalLatitude"])  # Also add for map compatibility
            except (ValueError, TypeError):
                pass
        
        if "decimalLongitude" in location:
            try:
                normalized["decimalLongitude"] = float(location["decimalLongitude"])
                normalized["longitude"] = float(location["decimalLongitude"])  # Also add for map compatibility
            except (ValueError, TypeError):
                pass

        # State/Province - Artportalen uses county.name
        if "county" in location and isinstance(location["county"], dict):
            normalized["stateProvince"] = location["county"].get("name")
        elif "municipality" in location and isinstance(location["municipality"], dict):
            normalized["stateProvince"] = location["municipality"].get("name")
        elif "stateProvince" in location:
            normalized["stateProvince"] = location["stateProvince"]
        elif "province" in location:
            normalized["stateProvince"] = location["province"]

        # Locality/Site Name - Artportalen API NOTE:
        # The Artportalen API does NOT return specific location names like "Vrångö" or "Stensjön"
        # It only returns municipality.name and county.name
        # Reverse geocoding is done lazily when formatting tooltips (not during normalization)
        # to avoid blocking initial data load
        
        location_name = None
        
        # Check for any location name fields in API response (unlikely but possible)
        if "site" in location:
            site_obj = location["site"]
            if isinstance(site_obj, dict):
                location_name = (site_obj.get("name") or 
                               site_obj.get("locationName") or 
                               site_obj.get("siteName") or
                               site_obj.get("locality"))
            elif isinstance(site_obj, str):
                location_name = site_obj
        
        if not location_name:
            location_name = (location.get("locationName") or 
                           location.get("siteName") or 
                           location.get("name") or
                           location.get("locality"))
        
        # If locality is a dict, extract name from it
        if not location_name and "locality" in location:
            if isinstance(location["locality"], dict):
                location_name = location["locality"].get("name")
        
        # Use municipality name as default locality (reverse geocoding happens lazily in tooltip)
        if "municipality" in location and isinstance(location["municipality"], dict):
            municipality_name = location["municipality"].get("name")
            if municipality_name:
                normalized["municipality"] = municipality_name
                # Set locality to municipality (will be replaced by reverse geocoding if available)
                normalized["locality"] = location_name or municipality_name

        # Coordinate uncertainty
        if "coordinateUncertaintyInMeters" in location:
            try:
                normalized["coordinateUncertaintyInMeters"] = float(location["coordinateUncertaintyInMeters"])
            except (ValueError, TypeError):
                pass

    # Country code - default to SE for Sweden
    if "countryCode" in record:
        normalized["countryCode"] = record["countryCode"]
    elif "country" in record:
        country = record["country"]
        if isinstance(country, str) and len(country) == 2:
            normalized["countryCode"] = country.upper()
        elif isinstance(country, dict):
            normalized["countryCode"] = country.get("code", country.get("countryCode", "SE"))
    else:
        normalized["countryCode"] = "SE"  # Default for Artportalen (Swedish data)

    # ===== OCCURRENCE INFORMATION =====
    # Artportalen uses nested occurrence object
    occurrence = record.get("occurrence", {})
    if isinstance(occurrence, dict):
        # Individual count
        if "individualCount" in occurrence:
            count_value = occurrence["individualCount"]
            if isinstance(count_value, str):
                try:
                    normalized["individualCount"] = int(count_value)
                except ValueError:
                    normalized["individualCount"] = count_value
            else:
                normalized["individualCount"] = count_value
        elif "count" in occurrence:
            normalized["individualCount"] = occurrence["count"]
        elif "quantity" in occurrence:
            normalized["individualCount"] = occurrence["quantity"]

        # Occurrence ID
        if "occurrenceId" in occurrence:
            normalized["id"] = occurrence["occurrenceId"]
        elif "occurrenceID" in occurrence:
            normalized["id"] = occurrence["occurrenceID"]

        # Occurrence status
        if "occurrenceStatus" in occurrence and isinstance(occurrence["occurrenceStatus"], dict):
            normalized["occurrenceStatus"] = occurrence["occurrenceStatus"].get("value")

    # Fallback for individual count if not in occurrence
    if "individualCount" not in normalized:
        if "individualCount" in record:
            normalized["individualCount"] = record["individualCount"]
        elif "count" in record:
            normalized["individualCount"] = record["count"]
        elif "quantity" in record:
            normalized["individualCount"] = record["quantity"]

    # ===== IDENTIFICATION INFORMATION =====
    # Artportalen uses nested identification object
    identification = record.get("identification", {})
    if isinstance(identification, dict):
        if "verified" in identification:
            normalized["identificationVerified"] = identification["verified"]
        if "uncertainIdentification" in identification:
            normalized["uncertainIdentification"] = identification["uncertainIdentification"]

    # ===== OBSERVER/RECORDER =====
    # Check various possible locations for observer info
    # Artportalen might have observer in different places
    observer_name = None
    
    # Check top-level fields first
    if "recordedBy" in record:
        observer_name = record["recordedBy"]
    elif "observer" in record:
        observer_name = record["observer"]
    elif "recorder" in record:
        observer_name = record["recorder"]
    elif "reportedBy" in record:
        observer_name = record["reportedBy"]
    
    # Check nested structures
    if not observer_name:
        # Check in event object
        if "event" in record and isinstance(record["event"], dict):
            observer_name = record["event"].get("recordedBy") or record["event"].get("observer")
        
        # Check in location object
        if not observer_name and "location" in record and isinstance(record["location"], dict):
            observer_name = record["location"].get("recordedBy") or record["location"].get("observer")
        
        # Check in occurrence object
        if not observer_name and "occurrence" in record and isinstance(record["occurrence"], dict):
            observer_name = record["occurrence"].get("recordedBy") or record["occurrence"].get("observer")
    
    if observer_name:
        normalized["recordedBy"] = observer_name

    # ===== BASIS OF RECORD =====
    if "basisOfRecord" in record:
        normalized["basisOfRecord"] = record["basisOfRecord"]
    elif "basisofrecord" in record:
        normalized["basisOfRecord"] = record["basisofrecord"]
    else:
        normalized["basisOfRecord"] = "HUMAN_OBSERVATION"  # Default for Artportalen

    # ===== DATASET INFORMATION =====
    if "datasetName" in record:
        normalized["datasetName"] = record["datasetName"]
    elif "dataset" in record:
        if isinstance(record["dataset"], dict):
            normalized["datasetName"] = record["dataset"].get("name") or record["dataset"].get("title")
        else:
            normalized["datasetName"] = str(record["dataset"])

    # ===== RECORD ID =====
    # Keep original record ID if available
    if "id" not in normalized:
        if "id" in record:
            normalized["id"] = record["id"]
        elif "sightingId" in record:
            normalized["id"] = record["sightingId"]
        elif "observationId" in record:
            normalized["id"] = record["observationId"]

    # ===== SOURCE INDICATOR =====
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

