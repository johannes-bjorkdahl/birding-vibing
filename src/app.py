"""Main Streamlit application for Swedish Bird Observations."""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
import sys
from pathlib import Path
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

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
        'Individual Count': record.get('individualCount') if record.get('individualCount') is not None else pd.NA,
        'Basis of Record': record.get('basisOfRecord', 'N/A'),
    }

    # Add coordinates if available
    if record.get('decimalLatitude') and record.get('decimalLongitude'):
        formatted['latitude'] = record['decimalLatitude']
        formatted['longitude'] = record['decimalLongitude']

    return formatted


def create_clustered_map(df: pd.DataFrame) -> folium.Map:
    """Create a Folium map with clustered markers for observations.

    Args:
        df: DataFrame containing observation data with latitude/longitude columns

    Returns:
        A folium.Map object with clustered markers, or None if no valid coordinates
    """
    # Check if required columns exist
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        return None
    
    # Filter for valid coordinates
    map_data = df[['latitude', 'longitude']].dropna()

    if map_data.empty:
        return None

    # Calculate map center
    center_lat = map_data['latitude'].mean()
    center_lon = map_data['longitude'].mean()

    # Create map centered on observations
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )

    # Create marker cluster
    marker_cluster = MarkerCluster(
        name='Observations',
        overlay=True,
        control=True,
        show=True
    ).add_to(m)

    # Add markers to cluster
    for idx, row in map_data.iterrows():
        # Get additional information for popup if available
        popup_text = f"Observation at ({row['latitude']:.4f}, {row['longitude']:.4f})"

        # Try to add species information if available in the dataframe
        if 'Scientific Name' in df.columns:
            species_name = df.loc[idx, 'Scientific Name']
            if pd.notna(species_name):
                popup_text = f"<b>{species_name}</b><br>" + popup_text

        if 'Common Name' in df.columns:
            common_name = df.loc[idx, 'Common Name']
            if pd.notna(common_name) and common_name != 'N/A':
                popup_text = popup_text.replace('<br>', f" ({common_name})<br>")

        if 'Date' in df.columns:
            obs_date = df.loc[idx, 'Date']
            if pd.notna(obs_date):
                popup_text += f"<br>Date: {obs_date}"

        # Add marker to cluster
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(marker_cluster)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


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

    # Date range filtering
    st.sidebar.subheader("Date Range")
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Default to a date range that should have data
    # Use system date, but if it's clearly in the future (year > current reasonable year),
    # default to recent dates from the previous year
    if today.year > 2024:  # If system date seems wrong (future), use 2024 dates
        # Default to a recent date range from 2024
        default_end = date(2024, 10, 31)
        default_start = date(2024, 10, 30)
    else:
        default_end = today
        default_start = yesterday
    
    # Use session state to preserve date selections
    # Reset to defaults if current dates are clearly in the future and have no data
    if 'start_date' not in st.session_state or 'end_date' not in st.session_state:
        st.session_state.start_date = default_start
        st.session_state.end_date = default_end
    elif st.session_state.start_date.year > 2024 or st.session_state.end_date.year > 2024:
        # If stored dates are in the future, reset to sensible defaults
        st.session_state.start_date = default_start
        st.session_state.end_date = default_end
    
    start_date = st.sidebar.date_input(
        "Start Date",
        value=st.session_state.start_date,
        max_value=today,
        help="Select the start date for observations"
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        value=st.session_state.end_date,
        max_value=today,
        help="Select the end date for observations"
    )
    
    # Validate date range
    if start_date > end_date:
        st.sidebar.error("Start date must be before or equal to end date.")
        end_date = start_date
    
    # Update session state
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    # Max results
    max_results = st.sidebar.slider(
        "Maximum results",
        min_value=10,
        max_value=300,
        value=100,
        step=10,
        help="Number of observations to retrieve (GBIF max: 300 per request)"
    )

    # Location filters
    st.sidebar.subheader("Location Filter")
    province = st.sidebar.text_input(
        "State/Province (optional)",
        help="Enter Swedish county/province name (e.g., 'Skåne', 'Stockholm')"
    )
    
    locality = st.sidebar.text_input(
        "Locality (optional)",
        help="Enter city/town name for more specific location filtering"
    )

    return {
        'start_date': start_date,
        'end_date': end_date,
        'max_results': max_results,
        'province': province if province else None,
        'locality': locality if locality else None
    }


def search_observations(search_params: Dict[str, Any]):
    """Execute observation search with given parameters."""
    with st.spinner("Searching GBIF for bird observations from Artportalen..."):
        start_date = search_params['start_date']
        end_date = search_params['end_date']
        today = datetime.now().date()
        days_span = (end_date - start_date).days
        is_recent = (today - end_date).days <= 7
        
        # For recent date ranges (within last 7 days), query each day separately
        # and combine results, as eventDate may not work reliably for very recent dates
        if is_recent and days_span <= 7 and days_span >= 0:
            # Query each day separately and combine
            all_results = []
            total_count = 0
            current_date = start_date
            
            while current_date <= end_date:
                day_result = st.session_state.api_client.search_occurrences(
                    taxon_key=Config.BIRDS_TAXON_KEY,
                    start_date=current_date,  # Single date uses year/month/day
                    country=Config.COUNTRY_CODE,
                    limit=min(300, search_params['max_results']),
                    state_province=search_params['province'],
                    locality=search_params.get('locality')
                )
                
                if 'error' not in day_result:
                    day_results = day_result.get('results', [])
                    all_results.extend(day_results)
                    total_count += day_result.get('count', 0)
                
                current_date += timedelta(days=1)
                
                # Limit total results to max_results
                if len(all_results) >= search_params['max_results']:
                    all_results = all_results[:search_params['max_results']]
                    break
            
            # Combine results
            result = {
                'results': all_results,
                'count': total_count
            }
        else:
            # For older date ranges, use normal date range query
            result = st.session_state.api_client.search_occurrences(
                taxon_key=Config.BIRDS_TAXON_KEY,
                start_date=start_date,
                end_date=end_date,
                country=Config.COUNTRY_CODE,
                limit=search_params['max_results'],
                state_province=search_params['province'],
                locality=search_params.get('locality')
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

        # Check if we got results - GBIF API returns results in 'results' array
        results = result.get('results', [])
        count = result.get('count', 0)
        
        # If no results but no error, check if we're querying future dates
        if not results and count == 0:
            today = datetime.now().date()
            # If querying recent dates (within last 30 days) with no results, might be future dates
            days_ahead = (search_params['start_date'] - today).days
            if days_ahead > 0:
                # Querying future dates - try to find most recent date with data
                st.warning(
                    f"No observations found for {search_params['start_date']} to {search_params['end_date']}. "
                    f"This date appears to be in the future. The most recent available data may be from earlier dates. "
                    "Try selecting a date range from the past year."
                )
            else:
                st.warning(
                    f"No observations found for the date range {search_params['start_date']} to {search_params['end_date']}. "
                    "Try adjusting your date range or filters."
                )
            # Still store the result so the UI can show the empty state
            st.session_state.observations_data = result
            st.session_state.last_search_params = search_params
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
        - 📅 Filter by date range and location
        - 🗺️ View observations on an interactive map with clustering
        - 📍 Automatic grouping of nearby observations for better visualization
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

    # Format records for display
    formatted_records = [format_observation_record(record) for record in results]

    if formatted_records:
        df = pd.DataFrame(formatted_records)

        # Display map if coordinates are available (before table)
        if 'latitude' in df.columns and 'longitude' in df.columns:
            st.subheader("Observation Locations")

            # Create clustered map
            clustered_map = create_clustered_map(df)

            if clustered_map is not None:
                # Display the map with clustering
                st_folium(
                    clustered_map,
                    width=None,  # Use full container width
                    height=600,
                    returned_objects=[]  # Don't track user interactions
                )

                # Add info about clustering
                st.info(
                    "🗺️ **Interactive Map with Clustering**: "
                    "Nearby observations are automatically grouped together. "
                    "Click on cluster circles to zoom in and see individual observations. "
                    "Click on markers to see observation details."
                )
            else:
                st.info("No coordinate data available for mapping.")

        # Display observations table
        st.subheader("Observations")

        # Display as interactive table
        st.dataframe(
            df,
            width='stretch',
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
    if st.sidebar.button("🔍 Search", type="primary", width='stretch'):
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
