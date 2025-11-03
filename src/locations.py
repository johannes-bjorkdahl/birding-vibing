"""Location configuration for Swedish counties, municipalities, and special areas."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum


class LocationType(Enum):
    """Type of location."""
    COUNTY = "county"
    MUNICIPALITY = "municipality"
    SPECIAL_AREA = "special_area"


@dataclass
class Location:
    """Location configuration."""
    id: str
    name: str
    type: LocationType
    province: Optional[str] = None  # County name (for municipalities and special areas)
    locality: Optional[str] = None  # Municipality name (for municipalities)
    municipalities: Optional[List[str]] = None  # List of municipality names (for special areas)

    def __str__(self) -> str:
        """Return display name with type indicator."""
        type_labels = {
            LocationType.COUNTY: "Län",
            LocationType.MUNICIPALITY: "Kommun",
            LocationType.SPECIAL_AREA: "Område"
        }
        return f"{self.name} ({type_labels[self.type]})"


# All 21 Swedish counties (län)
SWEDISH_COUNTIES = [
    Location(id="stockholm", name="Stockholm", type=LocationType.COUNTY),
    Location(id="vastra_gotaland", name="Västra Götaland", type=LocationType.COUNTY),
    Location(id="skane", name="Skåne", type=LocationType.COUNTY),
    Location(id="uppsala", name="Uppsala", type=LocationType.COUNTY),
    Location(id="vasterbotten", name="Västerbotten", type=LocationType.COUNTY),
    Location(id="orebro", name="Örebro", type=LocationType.COUNTY),
    Location(id="ostergotland", name="Östergötland", type=LocationType.COUNTY),
    Location(id="jamtland", name="Jämtland", type=LocationType.COUNTY),
    Location(id="sodermanland", name="Södermanland", type=LocationType.COUNTY),
    Location(id="dalarna", name="Dalarna", type=LocationType.COUNTY),
    Location(id="vastermorland", name="Västernorrland", type=LocationType.COUNTY),
    Location(id="gavleborg", name="Gävleborg", type=LocationType.COUNTY),
    Location(id="kronoberg", name="Kronoberg", type=LocationType.COUNTY),
    Location(id="kalmar", name="Kalmar", type=LocationType.COUNTY),
    Location(id="halland", name="Halland", type=LocationType.COUNTY),
    Location(id="varmland", name="Värmland", type=LocationType.COUNTY),
    Location(id="blekinge", name="Blekinge", type=LocationType.COUNTY),
    Location(id="jönköping", name="Jönköping", type=LocationType.COUNTY),
    Location(id="vastermanland", name="Västmanland", type=LocationType.COUNTY),
    Location(id="norrbotten", name="Norrbotten", type=LocationType.COUNTY),
]

# Common municipalities (kommuner)
COMMON_MUNICIPALITIES = [
    # Major cities
    Location(id="goteborg", name="Göteborg", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Göteborg"),
    Location(id="stockholm_kommun", name="Stockholm", type=LocationType.MUNICIPALITY, province="Stockholm", locality="Stockholm"),
    Location(id="malmo", name="Malmö", type=LocationType.MUNICIPALITY, province="Skåne", locality="Malmö"),
    Location(id="uppsala_kommun", name="Uppsala", type=LocationType.MUNICIPALITY, province="Uppsala", locality="Uppsala"),
    Location(id="vasteras", name="Västerås", type=LocationType.MUNICIPALITY, province="Västmanland", locality="Västerås"),
    Location(id="orebro_kommun", name="Örebro", type=LocationType.MUNICIPALITY, province="Örebro", locality="Örebro"),
    Location(id="linkoping", name="Linköping", type=LocationType.MUNICIPALITY, province="Östergötland", locality="Linköping"),
    Location(id="helsingborg", name="Helsingborg", type=LocationType.MUNICIPALITY, province="Skåne", locality="Helsingborg"),
    Location(id="jönköping_kommun", name="Jönköping", type=LocationType.MUNICIPALITY, province="Jönköping", locality="Jönköping"),
    Location(id="norrkoping", name="Norrköping", type=LocationType.MUNICIPALITY, province="Östergötland", locality="Norrköping"),
    Location(id="lund", name="Lund", type=LocationType.MUNICIPALITY, province="Skåne", locality="Lund"),
    Location(id="umea", name="Umeå", type=LocationType.MUNICIPALITY, province="Västerbotten", locality="Umeå"),
    Location(id="gavle", name="Gävle", type=LocationType.MUNICIPALITY, province="Gävleborg", locality="Gävle"),
    Location(id="boras", name="Borås", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Borås"),
    Location(id="eskilstuna", name="Eskilstuna", type=LocationType.MUNICIPALITY, province="Södermanland", locality="Eskilstuna"),
    Location(id="sodertalje", name="Södertälje", type=LocationType.MUNICIPALITY, province="Stockholm", locality="Södertälje"),
    Location(id="karlstad", name="Karlstad", type=LocationType.MUNICIPALITY, province="Värmland", locality="Karlstad"),
    Location(id="vaxjo", name="Växjö", type=LocationType.MUNICIPALITY, province="Kronoberg", locality="Växjö"),
    Location(id="halmstad", name="Halmstad", type=LocationType.MUNICIPALITY, province="Halland", locality="Halmstad"),
    Location(id="sundsvall", name="Sundsvall", type=LocationType.MUNICIPALITY, province="Västernorrland", locality="Sundsvall"),
    
    # Göteborg area municipalities
    Location(id="molndal", name="Mölndal", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Mölndal kommun"),
    Location(id="partille", name="Partille", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Partille kommun"),
    Location(id="kungälv", name="Kungälv", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Kungälv"),
    Location(id="alingsas", name="Alingsås", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Alingsås"),
    Location(id="lidkoping", name="Lidköping", type=LocationType.MUNICIPALITY, province="Västra Götaland", locality="Lidköping"),
]

# Special areas
SPECIAL_AREAS = [
    Location(
        id="goteborgsomradet",
        name="Göteborgsområdet",
        type=LocationType.SPECIAL_AREA,
        province="Västra Götaland",
        municipalities=["Göteborg", "Mölndal kommun", "Partille kommun"]
    ),
]

# Combined list of all locations
_all_locations: Optional[List[Location]] = None


def get_all_locations() -> List[Location]:
    """Get all available locations (counties, municipalities, and special areas).
    
    Returns:
        List of Location objects, sorted by type (special areas first, then counties, then municipalities)
        and alphabetically within each type.
    """
    global _all_locations
    
    if _all_locations is None:
        # Combine all locations
        _all_locations = SPECIAL_AREAS + SWEDISH_COUNTIES + COMMON_MUNICIPALITIES
        
        # Sort: special areas first, then counties, then municipalities
        # Within each type, sort alphabetically by name
        type_order = {
            LocationType.SPECIAL_AREA: 0,
            LocationType.COUNTY: 1,
            LocationType.MUNICIPALITY: 2,
        }
        
        _all_locations.sort(key=lambda loc: (type_order[loc.type], loc.name))
    
    return _all_locations


def get_location_by_id(location_id: str) -> Optional[Location]:
    """Get a location by its ID.
    
    Args:
        location_id: The location ID to look up
        
    Returns:
        Location object if found, None otherwise
    """
    for location in get_all_locations():
        if location.id == location_id:
            return location
    return None


def is_special_area(location_id: str) -> bool:
    """Check if a location is a special area requiring multiple API calls.
    
    Args:
        location_id: The location ID to check
        
    Returns:
        True if the location is a special area, False otherwise
    """
    location = get_location_by_id(location_id)
    return location is not None and location.type == LocationType.SPECIAL_AREA


def get_location_display_name(location_id: str) -> str:
    """Get the display name for a location.
    
    Args:
        location_id: The location ID
        
    Returns:
        Display name string, or the location_id if not found
    """
    location = get_location_by_id(location_id)
    if location:
        return str(location)
    return location_id


# Artportalen API feature ID mappings
# Based on Areas.md documentation: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/Areas.md
# County (Län) Feature IDs
COUNTY_FEATURE_IDS: Dict[str, str] = {
    "Stockholm": "1",
    "Uppsala": "3",
    "Södermanland": "4",
    "Östergötland": "5",
    "Jönköping": "6",
    "Kronoberg": "7",
    "Kalmar": "8",
    "Gotland": "9",
    "Blekinge": "10",
    "Skåne": "12",
    "Halland": "13",
    "Västra Götaland": "14",
    "Värmland": "17",
    "Örebro": "18",
    "Västmanland": "19",
    "Dalarna": "20",
    "Gävleborg": "21",
    "Västernorrland": "22",
    "Jämtland": "23",
    "Västerbotten": "24",
    "Norrbotten": "25",
}

# Municipality (Kommun) Feature IDs - partial mapping for common municipalities
# Full list would be too large, so we'll query the API for unknown municipalities
MUNICIPALITY_FEATURE_IDS: Dict[Tuple[str, str], str] = {
    # (municipality_name, county_name) -> feature_id
    # Common municipalities from Areas.md
    ("Göteborg", "Västra Götaland"): "1480",  # Göteborg kommun
    ("Stockholm", "Stockholm"): "180",  # Stockholm kommun
    ("Malmö", "Skåne"): "1280",  # Malmö kommun
    ("Uppsala", "Uppsala"): "380",  # Uppsala kommun
    ("Västerås", "Västmanland"): "1980",  # Västerås kommun
    ("Örebro", "Örebro"): "1880",  # Örebro kommun
    ("Linköping", "Östergötland"): "580",  # Linköping kommun
    ("Helsingborg", "Skåne"): "1283",  # Helsingborg kommun
    ("Jönköping", "Jönköping"): "680",  # Jönköping kommun
    ("Norrköping", "Östergötland"): "581",  # Norrköping kommun
    ("Lund", "Skåne"): "1281",  # Lund kommun
    ("Umeå", "Västerbotten"): "2480",  # Umeå kommun
    ("Gävle", "Gävleborg"): "2180",  # Gävle kommun
    ("Borås", "Västra Götaland"): "1490",  # Borås kommun
    ("Eskilstuna", "Södermanland"): "480",  # Eskilstuna kommun
    ("Södertälje", "Stockholm"): "181",  # Södertälje kommun
    ("Karlstad", "Värmland"): "1780",  # Karlstad kommun
    ("Växjö", "Kronoberg"): "780",  # Växjö kommun
    ("Halmstad", "Halland"): "1380",  # Halmstad kommun
    ("Sundsvall", "Västernorrland"): "2281",  # Sundsvall kommun
    ("Mölndal kommun", "Västra Götaland"): "1481",  # Mölndal kommun
    ("Partille kommun", "Västra Götaland"): "1407",  # Partille kommun
    ("Kungälv", "Västra Götaland"): "1482",  # Kungälv kommun
    ("Alingsås", "Västra Götaland"): "1484",  # Alingsås kommun
    ("Lidköping", "Västra Götaland"): "1494",  # Lidköping kommun
}


def get_county_feature_id(county_name: str) -> Optional[str]:
    """Get Artportalen feature ID for a county.
    
    Args:
        county_name: County name (e.g., "Västra Götaland")
        
    Returns:
        Feature ID as string, or None if not found
    """
    return COUNTY_FEATURE_IDS.get(county_name)


def get_municipality_feature_id(municipality_name: str, county_name: str) -> Optional[str]:
    """Get Artportalen feature ID for a municipality.
    
    Args:
        municipality_name: Municipality name (e.g., "Göteborg")
        county_name: County name (e.g., "Västra Götaland")
        
    Returns:
        Feature ID as string, or None if not found
    """
    # Try exact match first
    key = (municipality_name, county_name)
    if key in MUNICIPALITY_FEATURE_IDS:
        return MUNICIPALITY_FEATURE_IDS[key]
    
    # Try without " kommun" suffix
    if municipality_name.endswith(" kommun"):
        key = (municipality_name.replace(" kommun", ""), county_name)
        if key in MUNICIPALITY_FEATURE_IDS:
            return MUNICIPALITY_FEATURE_IDS[key]
    
    # Try with " kommun" suffix
    if not municipality_name.endswith(" kommun"):
        key = (f"{municipality_name} kommun", county_name)
        if key in MUNICIPALITY_FEATURE_IDS:
            return MUNICIPALITY_FEATURE_IDS[key]
    
    return None


def get_area_filter(state_province: Optional[str] = None, locality: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Build geographics filter for Artportalen API.
    
    Args:
        state_province: County name (for county-level or municipality-level filters)
        locality: Municipality name (for municipality-level filters)
        
    Returns:
        Geographics filter dict with areas array, or None if no valid location provided
    """
    areas = []
    
    if locality and state_province:
        # Municipality filter
        feature_id = get_municipality_feature_id(locality, state_province)
        if feature_id:
            areas.append({
                "areaType": "Municipality",
                "featureId": feature_id
            })
        else:
            # If municipality not found in mapping, try county fallback
            county_feature_id = get_county_feature_id(state_province)
            if county_feature_id:
                areas.append({
                    "areaType": "County",
                    "featureId": county_feature_id
                })
    elif state_province:
        # County filter only
        feature_id = get_county_feature_id(state_province)
        if feature_id:
            areas.append({
                "areaType": "County",
                "featureId": feature_id
            })
    
    if not areas:
        return None
    
    return {
        "geographics": {
            "areas": areas
        }
    }

