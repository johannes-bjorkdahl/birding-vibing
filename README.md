# 🐦 Birding Vibing

A Python application for exploring Swedish bird observations from Artportalen with **dual API support**: Real-time data via Artportalen API or historical data via GBIF API.

## Features

- 🔍 Search 116+ million bird observations from across Sweden
- ⚡ **Real-time data** via Artportalen API (when configured)
- 📚 **Historical data** via GBIF API (always available)
- 🔄 **Smart API selection** - automatically chooses the best API based on date range
- 📅 Filter by date range and location (province/county)
- 📊 View observation statistics and metrics
- 🗺️ Interactive map showing observation locations
- 💾 Export observations to CSV format
- 🎯 User-friendly Streamlit interface
- 🌍 **GBIF API requires no API key** - works out of the box!

## API Documentation & Troubleshooting

**For troubleshooting API issues, see:**
- [`docs/API_TROUBLESHOOTING.md`](docs/API_TROUBLESHOOTING.md) - Complete guide for API discovery, format, and debugging
- [`docs/API_CHANGES_LOG.md`](docs/API_CHANGES_LOG.md) - Log of API-related changes and fixes

**Quick API Info:**
- API Info Endpoint: `https://api.artdatabanken.se/species-observation-system/v1/api/ApiInfo`
- GitHub Documentation: https://github.com/biodiversitydata-se/SOS
- Search Filter Docs: https://github.com/biodiversitydata-se/SOS/blob/master/Docs/SearchFilter.md

## About the Data

This application accesses the **Artportalen** dataset, Sweden's national species observation system, through two APIs:

### Dual API Support

1. **Artportalen API** (Real-time)
   - **Update Frequency**: ~10 minutes (near real-time)
   - **Coverage**: Current day + recent observations
   - **Authentication**: Required (API key from api-portal.artdatabanken.se)
   - **Best for**: Recent observations (last 7-14 days)

2. **GBIF API** (Historical)
   - **Update Frequency**: Weekly updates
   - **Coverage**: Historical data (older than ~1 week)
   - **Authentication**: None required (public API)
   - **Best for**: Historical observations and when Artportalen API is not configured

- **116+ million observations** of plants, animals, and fungi
- **Open data** (CC0 license) - ~93% of observations freely accessible
- Managed by SLU Artdatabanken (Swedish University of Agricultural Sciences)
- Dataset ID: `38b4c89f-584c-41bb-bd8f-cd1def33e92f`

**View on GBIF:** https://www.gbif.org/dataset/38b4c89f-584c-41bb-bd8f-cd1def33e92f

## Prerequisites

- Python 3.11 or higher
- UV package manager

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd birding-vibing
   ```

2. **Install dependencies using UV:**
   ```bash
   uv sync
   ```

   If you don't have UV installed, install it first:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Configure Artportalen API (Optional):**
   
   For real-time data access, create a `.streamlit/secrets.toml` file in the project root:
   ```bash
   mkdir -p .streamlit
   ```
   
   Then create `.streamlit/secrets.toml` with your API key:
   ```toml
   ARTPORTALEN_SLU_API_KEY = "your_api_key_here"
   ```
   
   To obtain an API key:
   1. Register at [api-portal.artdatabanken.se](https://api-portal.artdatabanken.se/)
   2. Subscribe to the observation API product
   3. Copy your API key to the `.streamlit/secrets.toml` file
   
   **Note:** 
   - The application works without the Artportalen API key - it will automatically use GBIF API for all queries. Artportalen API is only needed for real-time recent observations.
   - Using `secrets.toml` is the recommended approach for Streamlit apps and simplifies deployment to Streamlit Community Cloud (you can paste the secrets directly in the deployment settings).
   - For backward compatibility, the app also checks environment variables if `secrets.toml` is not available.

## Usage

### Running the Application

**Option 1: Using the run script (Linux/Mac)**
```bash
./run.sh
```

**Option 2: Using UV directly**
```bash
uv run streamlit run src/app.py --server.port 8502
```

**Option 3: Manual activation**
```bash
source .venv/bin/activate
streamlit run src/app.py --server.port 8502
```

The application will open in your default web browser at `http://localhost:8502`.

### Using the Application

1. **Select Data Source (Optional):**
   - **Auto**: Automatically selects Artportalen for recent dates (last 7 days), GBIF for older dates
   - **Artportalen**: Force use of Artportalen API (real-time data)
   - **GBIF**: Force use of GBIF API (weekly updates)

2. **Select Date Range:**
   - Choose start and end dates for your search
   - Recent dates will automatically use Artportalen API if configured

3. **Configure Search:**
   - Adjust the maximum number of results (10-300 for GBIF, up to 1000 for Artportalen)
   - Optionally filter by Swedish province/county (e.g., "Skåne", "Stockholm")
   - Optionally filter by locality (city/town name)

4. **Search and Explore:**
   - Click "🔍 Search" to retrieve observations
   - View which API was used (shown in results)
   - View summary metrics (total observations, unique species, etc.)
   - Browse the interactive table of observations
   - View observation locations on the map
   - Download results as CSV

## Project Structure

```
birding-vibing/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Main Streamlit application
│   ├── config.py            # Configuration (dataset ID, API endpoints)
│   └── api/
│       ├── __init__.py      # API package initialization
│       ├── gbif_client.py   # GBIF API client
│       ├── artportalen_client.py  # Artportalen API client
│       ├── unified_client.py     # Smart API router
│       └── data_adapter.py   # Data normalization adapter
├── .streamlit/
│   └── secrets.toml         # API keys (gitignored) - use secrets.toml.example as template
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project dependencies and metadata
├── run.sh                   # Convenience script to run the app
└── README.md                # This file
```

## API Information

### GBIF API

This application uses the **GBIF API** for historical bird observation data:

- **Base URL:** https://api.gbif.org/v1
- **Authentication:** None required (public API)
- **Rate Limits:** Fair use policy, no hard limits for basic queries
- **Max Results:** 300 per request
- **Update Frequency:** Weekly

**Key Parameters:**
- **datasetKey:** `38b4c89f-584c-41bb-bd8f-cd1def33e92f` (Artportalen dataset)
- **taxonKey:** `212` (Aves - all birds in GBIF backbone taxonomy)
- **country:** `SE` (Sweden)

### Artportalen API

For real-time observations, the application can use the **Artportalen API**:

- **Base URL:** https://api.artdatabanken.se/species-observation-system/v1
- **Authentication:** Required (API key via subscription)
- **Update Frequency:** ~10 minutes (near real-time)
- **Max Results:** Up to 1000 per request
- **Coverage:** Recent observations (typically last 7-14 days)

**Setup:**
1. Register at [api-portal.artdatabanken.se](https://api-portal.artdatabanken.se/)
2. Subscribe to the observation API product
3. Add API key to `.streamlit/secrets.toml` file as `ARTPORTALEN_SLU_API_KEY` (recommended) or as an environment variable for backward compatibility

### API Documentation:
- [GBIF API Documentation](https://techdocs.gbif.org/en/openapi/)
- [GBIF API Beginner's Guide](https://data-blog.gbif.org/post/gbif-api-beginners-guide/)
- [Artportalen Developer Portal](https://api-portal.artdatabanken.se/)
- [Artportalen API Documentation](https://www.slu.se/artdatabanken/rapportering-och-fynd/oppna-data-och-apier/)
- [Artportalen Website](https://www.artportalen.se/)

## Development

### Adding Dependencies

```bash
uv add package-name
```

### Code Structure

The application is organized into modular components:

- **config.py** - Configuration constants (API URLs, dataset IDs, environment variables)
- **api/gbif_client.py** - GBIF API client
- **api/artportalen_client.py** - Artportalen API client
- **api/unified_client.py** - Smart API router that selects appropriate API
- **api/data_adapter.py** - Normalizes Artportalen responses to GBIF format
- **app.py** - Streamlit web interface

## Examples

### Example Search Queries

1. **All birds in current year:**
   - Time Period: "Current year"
   - Province: (leave empty)
   - Click Search

2. **Birds in Stockholm last 5 years:**
   - Time Period: "Last 5 years"
   - Province: "Stockholm"
   - Click Search

3. **Birds in specific month:**
   - Time Period: "Custom range"
   - Year: 2024-2024
   - Month: "May"
   - Click Search

## Troubleshooting

### Common Issues

**"No observations found"**
- Try expanding your date range
- Remove location filters
- Check that you're searching within valid years (data availability varies)

**"Search failed: HTTP error"**
- Check your internet connection
- API may be temporarily unavailable
- If using Artportalen API, verify your API key is correct and active
- Try again in a few moments

**"Artportalen API not configured"**
- This is normal if you haven't set up the Artportalen API key
- The app will automatically use GBIF API instead
- To enable real-time data, follow the Artportalen API setup instructions above

**Application won't start**
- Ensure all dependencies are installed: `uv sync`
- Check that you're using Python 3.11+: `python --version`
- Try running with `uv run streamlit run src/app.py`

**Map not showing**
- Some observations may not have coordinate data
- Check if the results include Latitude/Longitude columns

## Performance Notes

- **GBIF API** limits results to 300 per request
- **Artportalen API** supports up to 1000 results per request
- For large datasets, use specific filters to narrow your search
- Download options are available for further analysis
- The dataset contains 116+ million observations, so filtering is essential
- Recent dates (last 7 days) automatically use Artportalen API for faster, real-time data

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the LICENSE file for details.

The data accessed through this application is published under **CC0 1.0** (public domain dedication) by SLU Artdatabanken.

## Acknowledgments

- Data provided by [Artportalen](https://www.artportalen.se/) and [SLU Artdatabanken](https://www.artdatabanken.se/)
- Data accessed via [GBIF](https://www.gbif.org/) public API and [Artportalen API](https://api-portal.artdatabanken.se/)
- Built with [Streamlit](https://streamlit.io/)
- Package management by [UV](https://github.com/astral-sh/uv)

## Citation

If you use this data in research or publications, please cite:

```
Artportalen (Swedish Species Observation System).
SLU Artdatabanken, Swedish University of Agricultural Sciences.
Accessed via GBIF.org on [date].
Dataset: https://www.gbif.org/dataset/38b4c89f-584c-41bb-bd8f-cd1def33e92f
```

## Contact

For questions or support, please open an issue on the repository.

## Links

- **GBIF Dataset:** https://www.gbif.org/dataset/38b4c89f-584c-41bb-bd8f-cd1def33e92f
- **Artportalen:** https://www.artportalen.se/
- **Artportalen Developer Portal:** https://api-portal.artdatabanken.se/
- **SLU Artdatabanken:** https://www.artdatabanken.se/
- **GBIF:** https://www.gbif.org/
