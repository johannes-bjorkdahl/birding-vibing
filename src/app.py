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
from src.api_client import GBIFAPIClient


def init_session_state():
    """Initialize session state variables."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = GBIFAPIClient(
            Config.GBIF_API_BASE_URL,
            Config.DATASET_KEY
        )

    if 'observations_data' not in st.session_state:
        st.session_state.observations_data = None

    if 'last_search_params' not in st.session_state:
        st.session_state.last_search_params = None


def format_observation_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single observation record for display."""
    formatted = {
        'Date': record.get('eventDate', 'N/A'),
        'Year': record.get('year', 'N/A'),
        'Month': record.get('month', 'N/A'),
        'Day': record.get('day', 'N/A'),
        'Scientific Name': record.get('species', record.get('scientificName', 'N/A')),
        'Common Name': record.get('vernacularName', 'N/A'),
        'Locality': record.get('locality', 'N/A'),
        'State/Province': record.get('stateProvince', 'N/A'),
        'Country': record.get('countryCode', 'N/A'),
        'Observer': record.get('recordedBy', 'N/A'),
        'Individual Count': record.get('individualCount', 'N/A'),
        'Basis of Record': record.get('basisOfRecord', 'N/A'),
    }

    # Add coordinates if available
    if record.get('decimalLatitude') and record.get('decimalLongitude'):
        formatted['latitude'] = record['decimalLatitude']
        formatted['longitude'] = record['decimalLongitude']

    return formatted


def display_about_section():
    """Display information about the dataset."""
    st.sidebar.header("About the Data")

    with st.sidebar.expander("Dataset Information"):
        st.markdown("""
        **Artportalen - Swedish Species Observation System**

        - **116+ million** observations
        - **Weekly updates** from GBIF
        - **Open data** (CC0 license)
        - Managed by SLU Artdatabanken

        **No API key required!**
        This app uses the public GBIF API.
        """)

        if st.button("View Dataset on GBIF"):
            st.markdown(f"[Open GBIF Dataset](https://www.gbif.org/dataset/{Config.DATASET_KEY})")


def display_search_filters():
    """Display search filters and return search parameters."""
    st.sidebar.header("Search Filters")

    # Year range
    st.sidebar.subheader("Time Period")
    current_year = datetime.now().year

    date_option = st.sidebar.radio(
        "Select time period",
        ["Current year", "Last 5 years", "Custom range", "All time"]
    )

    start_year = None
    end_year = None
    month = None

    if date_option == "Current year":
        start_year = current_year
        end_year = current_year
    elif date_option == "Last 5 years":
        start_year = current_year - 5
        end_year = current_year
    elif date_option == "Custom range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_year = st.number_input(
                "From year",
                min_value=1900,
                max_value=current_year,
                value=current_year - 1
            )
        with col2:
            end_year = st.number_input(
                "To year",
                min_value=1900,
                max_value=current_year,
                value=current_year
            )

        # Optional month filter
        month_option = st.sidebar.selectbox(
            "Month (optional)",
            ["All months", "January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
        )
        if month_option != "All months":
            month = ["January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"].index(month_option) + 1

    # Max results
    max_results = st.sidebar.slider(
        "Maximum results",
        min_value=10,
        max_value=300,
        value=100,
        step=10,
        help="Number of observations to retrieve (GBIF max: 300 per request)"
    )

    # Province/county filter
    st.sidebar.subheader("Location Filter")
    province = st.sidebar.text_input(
        "State/Province (optional)",
        help="Enter Swedish county/province name (e.g., 'Skåne', 'Stockholm')"
    )

    return {
        'start_year': start_year,
        'end_year': end_year,
        'month': month,
        'max_results': max_results,
        'province': province if province else None
    }


def search_observations(search_params: Dict[str, Any]):
    """Execute observation search with given parameters."""
    with st.spinner("Searching GBIF for bird observations from Artportalen..."):
        result = st.session_state.api_client.search_occurrences(
            taxon_key=Config.BIRDS_TAXON_KEY,
            start_year=search_params['start_year'],
            end_year=search_params['end_year'],
            month=search_params['month'],
            country=Config.COUNTRY_CODE,
            limit=search_params['max_results'],
            state_province=search_params['province']
        )

        if 'error' in result:
            st.error(f"Search failed: {result['error']}")
            st.info(
                "Common issues:\n"
                "- Network connectivity problems\n"
                "- GBIF API temporarily unavailable\n"
                "- Invalid search parameters"
            )
            return

        # Store results in session state
        st.session_state.observations_data = result
        st.session_state.last_search_params = search_params


def display_observations():
    """Display the observations data."""
    if st.session_state.observations_data is None:
        st.info("Use the sidebar to configure search parameters and click 'Search' to view observations.")

        # Show example
        st.markdown("---")
        st.subheader("About This Application")
        st.markdown("""
        This application provides free access to Swedish bird observations from **Artportalen**,
        the Swedish Species Observation System, via the **GBIF public API**.

        **Features:**
        - 🔍 Search 116+ million observations
        - 📅 Filter by year, month, and location
        - 🗺️ View observations on an interactive map
        - 💾 Download data as CSV
        - 🌍 **No API key required** - completely free!

        **Get started by clicking the Search button in the sidebar!**
        """)
        return

    data = st.session_state.observations_data

    # Display summary
    st.header("Search Results")

    # Check for results
    results = data.get('results', [])
    total_count = data.get('count', 0)

    if not results:
        st.warning("No observations found for the given search criteria. Try adjusting your filters.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Results Shown", len(results))
    with col2:
        st.metric("Total Available", f"{total_count:,}")
    with col3:
        # Count unique species
        species = set()
        for record in results:
            species_name = record.get('species') or record.get('scientificName')
            if species_name:
                species.add(species_name)
        st.metric("Unique Species", len(species))
    with col4:
        # Get year range from results
        years = [r.get('year') for r in results if r.get('year')]
        if years:
            year_range = f"{min(years)}-{max(years)}"
            st.metric("Year Range", year_range)

    # Display observations table
    st.subheader("Observations")

    # Format records for display
    formatted_records = [format_observation_record(record) for record in results]

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
            label="📥 Download as CSV",
            data=csv,
            file_name=f"bird_observations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        # Display map if coordinates are available
        if 'latitude' in df.columns and 'longitude' in df.columns:
            map_data = df[['latitude', 'longitude']].dropna()
            if not map_data.empty:
                st.subheader("Observation Locations")
                st.map(map_data)
            else:
                st.info("No coordinate data available for mapping.")

        # Pagination info
        if total_count > len(results):
            st.info(
                f"Showing {len(results)} of {total_count:,} total observations. "
                f"The GBIF API limits results to 300 per request. "
                f"Use more specific filters to narrow your search."
            )

    # Show raw data in expander
    with st.expander("View Raw GBIF API Response"):
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
        "Explore bird observations from **Artportalen** (Swedish Species Observation System) "
        "via the **GBIF public API** - no API key required!"
    )

    # About section
    display_about_section()

    # Search filters
    search_params = display_search_filters()

    # Search button
    if st.sidebar.button("🔍 Search", type="primary", use_container_width=True):
        search_observations(search_params)

    # Display results
    display_observations()

    # Footer
    st.markdown("---")
    st.markdown(
        "Data from [Artportalen](https://www.artportalen.se/) via "
        "[GBIF](https://www.gbif.org/) • "
        f"[View Dataset](https://www.gbif.org/dataset/{Config.DATASET_KEY})"
    )


if __name__ == "__main__":
    main()
