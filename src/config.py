"""Configuration management for the application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Try multiple locations: current directory, project root, and parent directories
config_file = Path(__file__).resolve()
project_root = config_file.parent.parent
worktree_root = Path.cwd()

# Try loading .env from multiple locations (order matters - later loads override earlier)
env_paths = [
    worktree_root / '.env',  # Current working directory (most common)
    project_root / '.env',   # Project root (where .env should be)
    Path('/workspaces/birding-vibing/.env'),  # Original workspace location
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=False)  # Don't override if already loaded
        break
else:
    # Fallback: try default behavior (searches upward from current dir)
    load_dotenv()


def _get_api_key() -> str | None:
    """
    Get Artportalen API key from Streamlit secrets or environment variables.
    
    Priority order:
    1. Streamlit secrets.toml (recommended for Streamlit apps)
    2. Environment variables (for backward compatibility and non-Streamlit contexts)
    
    Returns:
        API key string if found, None otherwise
    """
    # Try Streamlit secrets first (recommended approach)
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            # Try to access the secret (handle both dict-like and attribute access)
            try:
                # Try dict-like access with .get() if available
                if hasattr(st.secrets, 'get'):
                    api_key = st.secrets.get("ARTPORTALEN_SLU_API_KEY")
                else:
                    # Fallback to direct access (may raise KeyError)
                    api_key = st.secrets["ARTPORTALEN_SLU_API_KEY"]
                
                if api_key:
                    return str(api_key)
            except (KeyError, AttributeError):
                # Key doesn't exist in secrets, fall through to env var
                pass
    except (ImportError, RuntimeError):
        # Streamlit not available or not in Streamlit context (e.g., tests)
        pass
    
    # Fallback to environment variable (backward compatibility)
    return os.getenv("ARTPORTALEN_SLU_API_KEY")


class Config:
    """Application configuration."""

    # GBIF API - Public, no authentication required
    GBIF_API_BASE_URL = "https://api.gbif.org/v1"

    # Swedish bird observations dataset on GBIF (Artportalen)
    DATASET_KEY = "38b4c89f-584c-41bb-bd8f-cd1def33e92f"

    # Birds taxon key in GBIF backbone taxonomy
    BIRDS_TAXON_KEY = 212  # Aves

    # Country code for Sweden
    COUNTRY_CODE = "SE"

    # Artportalen API configuration
    # Base URL for Artportalen API (from api-portal.artdatabanken.se)
    ARTPORTALEN_API_BASE_URL = os.getenv(
        "ARTPORTALEN_API_BASE_URL",
        "https://api.artdatabanken.se/species-observation-system/v1"
    )

    # Artportalen API key (optional - app falls back to GBIF if not set)
    # Loads from Streamlit secrets.toml first, then falls back to environment variables
    ARTPORTALEN_API_KEY = _get_api_key()

    # Date threshold for API selection (days)
    # Recent dates (within this threshold) will use Artportalen API
    # Historical dates (older) will use GBIF API
    ARTPORTALEN_DATE_THRESHOLD_DAYS = int(os.getenv("ARTPORTALEN_DATE_THRESHOLD_DAYS", "7"))

    # Artportalen taxon ID for birds (different from GBIF taxon key)
    # This is the taxon ID used in Artportalen's system
    ARTPORTALEN_BIRDS_TAXON_ID = int(os.getenv("ARTPORTALEN_BIRDS_TAXON_ID", "100012"))
    
    # Database configuration
    # Path to DuckDB database file
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/birds.duckdb")
    
    # Database date threshold (days)
    # Historical dates (older than this threshold) will use DuckDB
    # Recent dates (within this threshold) will use Artportalen API
    DATABASE_DATE_THRESHOLD_DAYS = int(os.getenv("DATABASE_DATE_THRESHOLD_DAYS", "30"))
    
    # Enable database usage (feature flag)
    USE_DATABASE = os.getenv("USE_DATABASE", "true").lower() in ("true", "1", "yes")