"""Lightweight reverse geocoding using OpenStreetMap Nominatim with persistent local cache."""
import httpx
from typing import Optional, Dict, Any
import time
import json
import os
from pathlib import Path

# Cache file location (in project root)
CACHE_FILE = Path(__file__).parent.parent.parent / ".location_cache.json"

# In-memory cache for this session
_cache: Dict[str, Optional[str]] = {}

def _load_cache() -> Dict[str, Optional[str]]:
    """Load cache from disk."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_cache(cache: Dict[str, Optional[str]]) -> None:
    """Save cache to disk."""
    try:
        # Create parent directory if it doesn't exist
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except IOError:
        # Fail silently if we can't write cache
        pass


def _get_cache_key(lat: float, lon: float) -> str:
    """Generate cache key from coordinates (rounded to ~100m precision)."""
    # Round to 4 decimal places (~11m precision) to group nearby coordinates
    return f"{round(lat, 4)},{round(lon, 4)}"


def _reverse_geocode_api(lat: float, lon: float) -> Optional[str]:
    """
    Reverse geocode coordinates to get location name using OpenStreetMap Nominatim API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Location name (e.g., "Vrångö") or None if not found
    """
    try:
        # Use Nominatim API with a small delay to respect rate limits
        # Nominatim allows 1 request per second (free tier)
        time.sleep(0.1)  # Small delay to be respectful
        
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
            "accept-language": "sv",  # Swedish language preference
            "zoom": 18,  # Higher zoom = more specific location names
        }
        
        headers = {
            "User-Agent": "BirdingVibing/1.0 (Swedish Bird Observations App)"
        }
        
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract location name from response
            address = data.get("address", {})
            
            # Try various fields in order of specificity
            # For Swedish locations, these fields often contain the specific place name
            location_name = (
                address.get("village") or  # Small villages/towns
                address.get("hamlet") or   # Small settlements
                address.get("suburb") or    # Suburbs/districts
                address.get("neighbourhood") or  # Neighborhoods
                address.get("locality") or  # Localities
                address.get("place") or     # Places
                address.get("town") or      # Towns
                address.get("city")         # Cities (fallback)
            )
            
            return location_name
            
    except Exception:
        # Fail silently - return None if reverse geocoding fails
        return None


def get_location_name(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """
    Get location name from coordinates using reverse geocoding with persistent cache.
    
    Args:
        lat: Latitude (optional)
        lon: Longitude (optional)
        
    Returns:
        Location name (e.g., "Vrångö") or None if coordinates invalid or lookup fails
    """
    if lat is None or lon is None:
        return None
    
    try:
        lat_float = float(lat)
        lon_float = float(lon)
        
        # Validate coordinates are reasonable (Sweden is roughly 55-69°N, 11-24°E)
        if not (55 <= lat_float <= 69) or not (11 <= lon_float <= 24):
            return None
        
        # Generate cache key
        cache_key = _get_cache_key(lat_float, lon_float)
        
        # Check in-memory cache first
        if cache_key in _cache:
            return _cache[cache_key]
        
        # Load persistent cache
        persistent_cache = _load_cache()
        
        # Check persistent cache
        if cache_key in persistent_cache:
            result = persistent_cache[cache_key]
            # Store in memory cache for faster access
            _cache[cache_key] = result
            return result
        
        # Not in cache - make API call
        location_name = _reverse_geocode_api(lat_float, lon_float)
        
        # Store in both caches
        _cache[cache_key] = location_name
        persistent_cache[cache_key] = location_name
        
        # Save to disk (async write would be better, but this is simpler)
        _save_cache(persistent_cache)
        
        return location_name
        
    except (ValueError, TypeError):
        return None
