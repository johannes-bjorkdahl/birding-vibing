"""Configuration management for the application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    API_KEY = os.getenv("API_KEY", "")
    API_BASE_URL = os.getenv("API_BASE_URL", "https://api.artdatabanken.se/species-observation-system/v1")

    # Birds taxon ID in the Swedish taxonomy
    BIRDS_TAXON_ID = 4000104

    @classmethod
    def is_configured(cls) -> bool:
        """Check if the API is properly configured."""
        return bool(cls.API_KEY and cls.API_KEY != "your_api_key_here")
