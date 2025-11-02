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
from src.api.gbif_client import GBIFAPIClient
from src.api.artportalen_client import ArtportalenAPIClient
from src.api.unified_client import UnifiedAPIClient


def init_session_state():
    """Initialize session state variables."""
    if 'unified_client' not in st.session_state:
        # Initialize GBIF client
        gbif_client = GBIFAPIClient(
            Config.GBIF_API_BASE_URL,
            Config.DATASET_KEY
        )
        
        # Initialize Artportalen client if API key is available
        artportalen_client = None
        if Config.ARTPORTALEN_API_KEY:
            artportalen_client = ArtportalenAPIClient(
                Config.ARTPORTALEN_API_BASE_URL,
                Config.ARTPORTALEN_API_KEY
            )
        
        # Create unified client
        st.session_state.unified_client = UnifiedAPIClient(
            gbif_client=gbif_client,
            artportalen_client=artportalen_client,
            date_threshold_days=Config.ARTPORTALEN_DATE_THRESHOLD_DAYS
        )

    if 'observations_data' not in st.session_state:
        st.session_state.observations_data = None

    if 'last_search_params' not in st.session_state:
        st.session_state.last_search_params = None
    
    if 'api_selection' not in st.session_state:
        st.session_state.api_selection = "auto"


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

    # Add coordinates if available (for map display)
    # Check both decimalLatitude/decimalLongitude and latitude/longitude
    lat = record.get('latitude') or record.get('decimalLatitude')
    lon = record.get('longitude') or record.get('decimalLongitude')
    if lat is not None and lon is not None:
        formatted['latitude'] = lat
        formatted['longitude'] = lon

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
        - **Dual API support**: Real-time (Artportalen) + Historical (GBIF)
        - **Open data** (CC0 license)
        - Managed by SLU Artdatabanken
        """)

        # Show API availability
        api_info = st.session_state.unified_client.get_current_api_info()
        st.markdown("**API Status:**")
        st.markdown(f"- ✅ GBIF API: Available")
        if api_info["artportalen_available"]:
            st.markdown(f"- ✅ Artportalen API: Available (Real-time)")
        else:
            st.markdown(f"- ⚠️ Artportalen API: Not configured (using GBIF only)")

        if st.button("View Dataset on GBIF"):
            st.markdown(f"[Open GBIF Dataset](https://www.gbif.org/dataset/{Config.DATASET_KEY})")


def display_search_filters():
    """Display search filters and return search parameters."""
    st.sidebar.header("Search Filters")

    # API Selection
    st.sidebar.subheader("Data Source")
    api_info = st.session_state.unified_client.get_current_api_info()
    
    api_options = ["auto"]
    api_labels = ["Auto (Smart Selection)"]
    
    if api_info["artportalen_available"]:
        api_options.extend(["artportalen", "gbif"])
        api_labels.extend(["Artportalen (Real-time)", "GBIF (Historical)"])
    else:
        api_options.append("gbif")
        api_labels.append("GBIF (Historical)")
    
    api_selection_idx = api_options.index(st.session_state.api_selection) if st.session_state.api_selection in api_options else 0
    selected_api = st.sidebar.selectbox(
        "API Source",
        options=api_options,
        format_func=lambda x: api_labels[api_options.index(x)],
        index=api_selection_idx,
        help="Auto: Recent dates use Artportalen (real-time), older dates use GBIF (weekly updates)"
    )
    st.session_state.api_selection = selected_api
    
    if selected_api == "auto":
        st.sidebar.caption(f"🔄 Auto-selection: Recent ({Config.ARTPORTALEN_DATE_THRESHOLD_DAYS} days) → Artportalen, Older → GBIF")
    elif selected_api == "artportalen":
        st.sidebar.caption("⚡ Using Artportalen API (Real-time data)")
    else:
        st.sidebar.caption("📚 Using GBIF API (Weekly updates)")

    # Date range filtering
    st.sidebar.subheader("Date Range")
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Default to current day and the day before
    default_end = today
    default_start = yesterday
    
    # Use session state to preserve date selections
    # Initialize defaults if not already set, or reset if dates are outdated/future
    should_reset_dates = False
    if 'start_date' not in st.session_state or 'end_date' not in st.session_state:
        should_reset_dates = True
    else:
        # Reset if dates are in the future or too old (more than 7 days ago)
        # This ensures we always default to recent dates for current day data
        stored_start = st.session_state.start_date
        stored_end = st.session_state.end_date
        
        if stored_end and stored_start:
            days_old = (today - stored_end).days
            # Reset if dates are future, very old, or more than 7 days old
            if stored_end > today or stored_start > today or days_old > 7:
                should_reset_dates = True
        else:
            should_reset_dates = True
    
    if should_reset_dates:
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
        'locality': locality if locality else None,
        'api_selection': selected_api
    }


def search_observations(search_params: Dict[str, Any]):
    """Execute observation search with given parameters."""
    start_date = search_params['start_date']
    end_date = search_params['end_date']
    api_selection = search_params.get('api_selection', 'auto')
    
    # Determine which API will be used for the spinner message
    api_info = st.session_state.unified_client.get_current_api_info()
    use_artportalen, reason = st.session_state.unified_client._should_use_artportalen(
        start_date, end_date, api_selection
    )
    
    if use_artportalen:
        spinner_msg = "Searching Artportalen API for real-time bird observations..."
    else:
        spinner_msg = "Searching GBIF API for bird observations from Artportalen..."
    
    with st.spinner(spinner_msg):
        # Use unified client with forced API selection if specified
        result = st.session_state.unified_client.search_occurrences(
            taxon_key=Config.BIRDS_TAXON_KEY,
            taxon_id=Config.ARTPORTALEN_BIRDS_TAXON_ID,
            start_date=start_date,
            end_date=end_date,
            country=Config.COUNTRY_CODE,
            limit=search_params['max_results'],
            state_province=search_params['province'],
            locality=search_params.get('locality'),
            force_api=api_selection
        )

        if 'error' in result:
            api_source = result.get('_api_source', 'unknown')
            error_msg = result['error']
            
            st.error(f"Search failed ({api_source.upper()}): {error_msg}")
            
            if api_source == 'artportalen':
                st.info(
                    "Artportalen API issues:\n"
                    "- Check your API key configuration\n"
                    "- Verify API key is valid and active\n"
                    "- API may be temporarily unavailable\n"
                    "\nFalling back to GBIF API..."
                )
            else:
                st.info(
                    "Common issues:\n"
                    "- Network connectivity problems\n"
                    "- GBIF API temporarily unavailable\n"
                    "- Invalid search parameters"
                )
            return

        # Check if we got results
        results = result.get('results', [])
        count = result.get('count', 0)
        api_source = result.get('_api_source', 'gbif')
        api_reason = result.get('_api_selection_reason', 'unknown')
        artportalen_error = result.get('_artportalen_error')
        
        # Show API source info
        if api_source == 'artportalen':
            st.success("✅ Using Artportalen API (Real-time data)")
        else:
            if api_reason == 'artportalen_unavailable':
                st.info("ℹ️ Artportalen API not configured - using GBIF API (Weekly updates)")
            elif api_reason == 'historical_date_range':
                st.info("ℹ️ Historical date range - using GBIF API (Weekly updates)")
            elif artportalen_error:
                # Show warning if Artportalen failed and we fell back
                st.warning(f"⚠️ Artportalen API failed ({artportalen_error}) - using GBIF API (Weekly updates)")
            else:
                st.info("ℹ️ Using GBIF API (Weekly updates)")
        
        # If no results but no error, check if we're querying future dates or very recent dates
        if not results and count == 0:
            today = datetime.now().date()
            days_ahead = (search_params['start_date'] - today).days
            days_behind = (today - search_params['end_date']).days
            
            if days_ahead > 0:
                # Future dates - check if it's way in the future
                if days_ahead > 365:
                    st.warning(
                        f"⚠️ No observations found for {search_params['start_date']} to {search_params['end_date']}. "
                        f"These dates are in the future. "
                        f"**Available data through Artportalen API currently goes up to approximately May 2020.** "
                        f"Please try searching with dates from 2020 or earlier, or use GBIF API for historical data."
                    )
                else:
                    st.warning(
                        f"No observations found for {search_params['start_date']} to {search_params['end_date']}. "
                        f"This date appears to be in the future. The most recent available data may be from earlier dates. "
                        "Try selecting a date range from 2020 or earlier."
                    )
            elif api_source == 'artportalen' and days_behind > 1800:  # More than ~5 years ago from today
                st.warning(
                    f"⚠️ No observations found for {search_params['start_date']} to {search_params['end_date']}. "
                    f"**Note:** Artportalen API data availability is limited. The most recent data available may be from 2020 or earlier. "
                    f"Try searching with dates from 2018-2020, or use GBIF API which has more historical data."
                )
            elif days_behind <= 2 and api_source == 'gbif':
                st.info(
                    f"No observations found for {search_params['start_date']} to {search_params['end_date']}. "
                    "Very recent dates may not be available in GBIF API as it updates weekly. "
                    "Try using Artportalen API for real-time data, or search with dates from a few days ago."
                )
            else:
                st.warning(
                    f"No observations found for the date range {search_params['start_date']} to {search_params['end_date']}. "
                    "Try adjusting your date range or filters. "
                    f"**Tip:** Artportalen API data is available up to approximately May 2020. "
                    f"For dates after that, try using GBIF API or search with earlier dates."
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
    api_source = data.get('_api_source', 'gbif')

    if not results:
        st.warning("No observations found for the given search criteria. Try adjusting your filters.")
        return

    # Show data source badge
    if api_source == 'artportalen':
        st.success("📡 **Data Source:** Artportalen API (Real-time observations)")
    else:
        st.info("📚 **Data Source:** GBIF API (Weekly updates from Artportalen)")

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
            api_name = "Artportalen" if api_source == 'artportalen' else "GBIF"
            max_limit = 1000 if api_source == 'artportalen' else 300
            st.info(
                f"Showing {len(results)} of {total_count:,} total observations. "
                f"The {api_name} API limits results to {max_limit} per request. "
                f"Use more specific filters to narrow your search."
            )

    # Show raw data in expander
    api_name = "Artportalen" if api_source == 'artportalen' else "GBIF"
    with st.expander(f"View Raw {api_name} API Response"):
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
        "with **dual API support**: Real-time data via Artportalen API or historical data via GBIF API."
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
    api_info = st.session_state.unified_client.get_current_api_info()
    if api_info["artportalen_available"]:
        st.markdown(
            "Data from [Artportalen](https://www.artportalen.se/) via "
            "[Artportalen API](https://api-portal.artdatabanken.se/) (real-time) and "
            "[GBIF](https://www.gbif.org/) (historical) • "
            f"[View Dataset](https://www.gbif.org/dataset/{Config.DATASET_KEY})"
        )
    else:
        st.markdown(
            "Data from [Artportalen](https://www.artportalen.se/) via "
            "[GBIF](https://www.gbif.org/) • "
            f"[View Dataset](https://www.gbif.org/dataset/{Config.DATASET_KEY})"
        )


if __name__ == "__main__":
    main()
