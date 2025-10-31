"""Configuration management for the application."""


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
