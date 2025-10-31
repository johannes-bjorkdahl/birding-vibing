"""Main Streamlit application for Swedish Bird Observations."""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.api_client import ArtdatabankenAPIClient


def init_session_state():
    """Initialize session state variables."""
    if 'api_client' not in st.session_state:
        if Config.is_configured():
            st.session_state.api_client = ArtdatabankenAPIClient(
                Config.API_KEY,
                Config.API_BASE_URL
            )
        else:
            st.session_state.api_client = None

    if 'observations_data' not in st.session_state:
        st.session_state.observations_data = None

    if 'last_search_params' not in st.session_state:
        st.session_state.last_search_params = None


def format_observation_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single observation record for display."""
    # Extract key fields from the observation record
    # Note: Field names may vary based on API response structure
    formatted = {
        'Date': record.get('event', {}).get('startDate', 'N/A'),
        'Species': record.get('taxon', {}).get('scientificName', 'N/A'),
        'Common Name': record.get('taxon', {}).get('vernacularName', 'N/A'),
        'Location': record.get('location', {}).get('locality', 'N/A'),
        'Observer': record.get('recordedBy', 'N/A'),
        'Count': record.get('occurrence', {}).get('individualCount', 'N/A'),
    }

    # Add coordinates if available
    if 'location' in record and 'decimalLatitude' in record['location']:
        formatted['Latitude'] = record['location'].get('decimalLatitude')
        formatted['Longitude'] = record['location'].get('decimalLongitude')

    return formatted


def display_api_configuration():
    """Display API configuration section."""
    st.sidebar.header("API Configuration")

    if Config.is_configured():
        st.sidebar.success("API Key configured")

        # Allow manual API key input to override
        with st.sidebar.expander("Override API Key"):
            manual_key = st.text_input(
                "API Key",
                type="password",
                help="Enter your Artdatabanken API key"
            )
            if st.button("Update API Key"):
                if manual_key:
                    st.session_state.api_client = ArtdatabankenAPIClient(
                        manual_key,
                        Config.API_BASE_URL
                    )
                    st.success("API key updated!")
                    st.rerun()
    else:
        st.sidebar.warning("API Key not configured")
        st.sidebar.info(
            "To use this application, you need an API key from Artdatabanken. "
            "Visit https://api-portal.artdatabanken.se/ to sign up and get your key."
        )

        manual_key = st.sidebar.text_input(
            "Enter API Key",
            type="password",
            help="Paste your Artdatabanken API key here"
        )

        if st.sidebar.button("Set API Key"):
            if manual_key:
                st.session_state.api_client = ArtdatabankenAPIClient(
                    manual_key,
                    Config.API_BASE_URL
                )
                st.sidebar.success("API key set! You can now search for observations.")
                st.rerun()
            else:
                st.sidebar.error("Please enter a valid API key")


def display_search_filters():
    """Display search filters and return search parameters."""
    st.sidebar.header("Search Filters")

    # Date range
    st.sidebar.subheader("Date Range")
    date_option = st.sidebar.radio(
        "Select date range",
        ["Last 7 days", "Last 30 days", "Custom range", "All time"]
    )

    start_date = None
    end_date = None

    if date_option == "Last 7 days":
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
    elif date_option == "Last 30 days":
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    elif date_option == "Custom range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("From", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("To", value=date.today())

    # Max results
    max_results = st.sidebar.slider(
        "Maximum results",
        min_value=10,
        max_value=1000,
        value=100,
        step=10,
        help="Number of observations to retrieve"
    )

    # Province filter (optional - can be expanded with actual province list)
    st.sidebar.subheader("Location")
    province = st.sidebar.text_input(
        "Province (optional)",
        help="Enter Swedish province name to filter by location"
    )

    return {
        'start_date': start_date,
        'end_date': end_date,
        'max_results': max_results,
        'province': province if province else None
    }


def search_observations(search_params: Dict[str, Any]):
    """Execute observation search with given parameters."""
    if st.session_state.api_client is None:
        st.error("Please configure your API key first.")
        return

    with st.spinner("Searching for bird observations..."):
        result = st.session_state.api_client.search_observations(
            taxon_ids=[Config.BIRDS_TAXON_ID],
            start_date=search_params['start_date'],
            end_date=search_params['end_date'],
            max_results=search_params['max_results'],
            province=search_params['province']
        )

        if 'error' in result:
            st.error(f"Search failed: {result['error']}")
            st.info(
                "Common issues:\n"
                "- Invalid API key\n"
                "- API subscription not active\n"
                "- Network connectivity issues\n"
                "- API rate limits exceeded"
            )
            return

        # Store results in session state
        st.session_state.observations_data = result
        st.session_state.last_search_params = search_params


def display_observations():
    """Display the observations data."""
    if st.session_state.observations_data is None:
        st.info("Use the sidebar to configure search parameters and click 'Search' to view observations.")
        return

    data = st.session_state.observations_data

    # Display summary
    st.header("Search Results")

    # Check for records
    records = data.get('records', [])

    if not records:
        st.warning("No observations found for the given search criteria.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Observations", len(records))
    with col2:
        # Count unique species
        species = set()
        for record in records:
            taxon = record.get('taxon', {})
            species_name = taxon.get('scientificName')
            if species_name:
                species.add(species_name)
        st.metric("Unique Species", len(species))
    with col3:
        # Get date range
        if st.session_state.last_search_params:
            params = st.session_state.last_search_params
            if params['start_date'] and params['end_date']:
                days = (params['end_date'] - params['start_date']).days
                st.metric("Date Range (days)", days)

    # Display observations table
    st.subheader("Observations")

    # Format records for display
    formatted_records = [format_observation_record(record) for record in records]

    if formatted_records:
        df = pd.DataFrame(formatted_records)

        # Display as interactive table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"bird_observations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        # Display map if coordinates are available
        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            map_data = df[['Latitude', 'Longitude']].dropna()
            if not map_data.empty:
                st.subheader("Observation Locations")
                st.map(map_data)

    # Show raw data in expander
    with st.expander("View Raw API Response"):
        st.json(data)


def main():
    """Main application function."""
    st.set_page_config(
        page_title="Swedish Bird Observations",
        page_icon="🐦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Header
    st.title("🐦 Swedish Bird Observations")
    st.markdown(
        "Explore bird observations from the Swedish Species Observation System "
        "(Artportalen) powered by Artdatabanken."
    )

    # API configuration
    display_api_configuration()

    # Only show search if API is configured
    if st.session_state.api_client:
        # Search filters
        search_params = display_search_filters()

        # Search button
        if st.sidebar.button("🔍 Search", type="primary", use_container_width=True):
            search_observations(search_params)

        # Display results
        display_observations()
    else:
        st.warning(
            "Please configure your API key in the sidebar to start exploring bird observations."
        )

        # Information about the API
        st.info(
            "**How to get started:**\n\n"
            "1. Visit [Artdatabanken API Portal](https://api-portal.artdatabanken.se/)\n"
            "2. Create an account and sign up\n"
            "3. Subscribe to the Species Observation System API\n"
            "4. Copy your API key\n"
            "5. Paste it in the sidebar to start exploring bird observations!"
        )

        st.markdown("---")
        st.subheader("About this Application")
        st.markdown(
            "This application provides access to Swedish bird observations from Artportalen, "
            "the Swedish Species Observation System. You can search, filter, and download "
            "bird observation data from across Sweden."
        )


if __name__ == "__main__":
    main()
