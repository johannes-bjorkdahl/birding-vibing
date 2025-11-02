# 🐦 Birding Vibing

A Python application for exploring Swedish bird observations from Artportalen via the GBIF public API.

## Features

- 🔍 Search 116+ million bird observations from across Sweden
- 📅 Filter by year, month, and location (province/county)
- 📊 View observation statistics and metrics
- 🗺️ Interactive map showing observation locations
- 💾 Export observations to CSV format
- 🎯 User-friendly Streamlit interface
- 🌍 **No API key required** - uses free GBIF public API!

## About the Data

This application accesses the **Artportalen** dataset, Sweden's national species observation system, through the **GBIF (Global Biodiversity Information Facility)** public API.

- **116+ million observations** of plants, animals, and fungi
- **Weekly updates** from Artportalen
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

That's it! No API keys or configuration needed.

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

1. **Select Time Period:**
   - Current year
   - Last 5 years
   - Custom range (with optional month filter)
   - All time

2. **Configure Search:**
   - Adjust the maximum number of results (10-300)
   - Optionally filter by Swedish province/county (e.g., "Skåne", "Stockholm")

3. **Search and Explore:**
   - Click "🔍 Search" to retrieve observations
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
│   ├── api_client.py        # GBIF API client
│   └── config.py            # Configuration (dataset ID, API endpoints)
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project dependencies and metadata
├── run.sh                   # Convenience script to run the app
└── README.md                # This file
```

## API Information

This application uses the **GBIF API** to access bird observation data:

- **Base URL:** https://api.gbif.org/v1
- **Authentication:** None required (public API)
- **Rate Limits:** Fair use policy, no hard limits for basic queries
- **Max Results:** 300 per request

### Key Parameters:
- **datasetKey:** `38b4c89f-584c-41bb-bd8f-cd1def33e92f` (Artportalen dataset)
- **taxonKey:** `212` (Aves - all birds in GBIF backbone taxonomy)
- **country:** `SE` (Sweden)

### API Documentation:
- [GBIF API Documentation](https://techdocs.gbif.org/en/openapi/)
- [GBIF API Beginner's Guide](https://data-blog.gbif.org/post/gbif-api-beginners-guide/)
- [Artportalen Website](https://www.artportalen.se/)

## Development

### Adding Dependencies

```bash
uv add package-name
```

### Code Structure

The application is organized into three main modules:

- **config.py** - Configuration constants (API URLs, dataset IDs)
- **api_client.py** - GBIF API client with methods for searching observations
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
- GBIF API may be temporarily unavailable
- Try again in a few moments

**Application won't start**
- Ensure all dependencies are installed: `uv sync`
- Check that you're using Python 3.11+: `python --version`
- Try running with `uv run streamlit run src/app.py`

**Map not showing**
- Some observations may not have coordinate data
- Check if the results include Latitude/Longitude columns

## Performance Notes

- GBIF API limits results to 300 per request
- For large datasets, use specific filters to narrow your search
- Download options are available for further analysis
- The dataset contains 116+ million observations, so filtering is essential

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the LICENSE file for details.

The data accessed through this application is published under **CC0 1.0** (public domain dedication) by SLU Artdatabanken.

## Acknowledgments

- Data provided by [Artportalen](https://www.artportalen.se/) and [SLU Artdatabanken](https://www.artdatabanken.se/)
- Data accessed via [GBIF](https://www.gbif.org/) public API
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
- **SLU Artdatabanken:** https://www.artdatabanken.se/
- **GBIF:** https://www.gbif.org/
