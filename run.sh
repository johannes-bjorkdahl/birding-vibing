#!/bin/bash
# Run the Streamlit application

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run Streamlit
uv run streamlit run src/app.py
