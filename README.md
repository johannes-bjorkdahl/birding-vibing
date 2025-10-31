# 🐦 Birding Vibing

A Python application for exploring Swedish bird observations from the Artdatabanken Species Observation System (Artportalen).

## Features

- 🔍 Search and filter bird observations from across Sweden
- 📅 Filter by date ranges (last 7 days, last 30 days, custom range, or all time)
- 📊 View observation statistics and metrics
- 🗺️ Interactive map showing observation locations
- 💾 Export observations to CSV format
- 🎯 User-friendly Streamlit interface

## Prerequisites

- Python 3.11 or higher
- UV package manager
- API key from Artdatabanken (see setup instructions below)

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

3. **Configure your API key:**

   You need an API key from Artdatabanken to access the bird observation data.

   **Get your API key:**
   - Visit [Artdatabanken API Portal](https://api-portal.artdatabanken.se/)
   - Create an account and sign up
   - Subscribe to the "Species Observation System" API
   - Copy your API subscription key

   **Option 1: Using environment variables (recommended)**

   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API key:
   ```
   API_KEY=your_actual_api_key_here
   API_BASE_URL=https://api.artdatabanken.se/species-observation-system/v1
   ```

   **Option 2: Enter API key in the application**

   You can also enter your API key directly in the Streamlit sidebar when running the application.

## Usage

### Running the Application

**Option 1: Using the run script (Linux/Mac)**
```bash
./run.sh
```

**Option 2: Using UV directly**
```bash
uv run streamlit run src/app.py
```

**Option 3: Manual activation**
```bash
source .venv/bin/activate
streamlit run src/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Using the Application

1. **Configure API Key:**
   - If you haven't set up a `.env` file, enter your API key in the sidebar
   - Click "Set API Key" to activate

2. **Search for Observations:**
   - Select a date range (Last 7 days, Last 30 days, Custom, or All time)
   - Adjust the maximum number of results (10-1000)
   - Optionally filter by Swedish province
   - Click "🔍 Search" to retrieve observations

3. **View Results:**
   - See summary metrics (total observations, unique species, date range)
   - Browse the interactive table of observations
   - View observation locations on the map
   - Download results as CSV

## Project Structure

```
birding-vibing/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Main Streamlit application
│   ├── api_client.py        # Artdatabanken API client
│   └── config.py            # Configuration management
├── .env.example             # Example environment variables
├── .gitignore              # Git ignore rules
├── pyproject.toml          # Project dependencies and metadata
├── run.sh                  # Convenience script to run the app
└── README.md               # This file
```

## API Information

This application uses the **Artdatabanken Species Observation System API** to access bird observation data from Artportalen, Sweden's national species observation system.

### Key Features:
- Access to thousands of bird observations across Sweden
- Filter by species, date, location, and more
- Real-time data from citizen scientists and researchers
- Comprehensive observation metadata

### API Documentation:
- [API Portal](https://api-portal.artdatabanken.se/)
- [Artdatabanken Website](https://www.artdatabanken.se/)

## Development

### Adding Dependencies

```bash
uv add package-name
```

### Running Tests

```bash
uv run pytest
```

## Troubleshooting

### Common Issues

**"API Key not configured"**
- Ensure you've created a `.env` file with your API key
- Or enter your API key manually in the sidebar

**"Search failed: HTTP error 401"**
- Your API key is invalid or expired
- Check that you've subscribed to the correct API product
- Verify your API key at the [API Portal](https://api-portal.artdatabanken.se/)

**"Search failed: HTTP error 429"**
- You've exceeded the API rate limit
- Wait a few minutes before trying again
- Consider reducing the number of requests

**"No observations found"**
- Try expanding your date range
- Remove province filters
- Check that there are observations for your search criteria

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the LICENSE file for details.

## Acknowledgments

- Data provided by [Artdatabanken](https://www.artdatabanken.se/) (Swedish Species Information Centre)
- Built with [Streamlit](https://streamlit.io/)
- Package management by [UV](https://github.com/astral-sh/uv)

## Contact

For questions or support, please open an issue on the repository.
