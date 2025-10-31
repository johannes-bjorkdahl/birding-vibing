#!/bin/bash
# Run the Streamlit application using UV

# Ensure UV is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Run Streamlit using UV (automatically uses .venv created by uv sync)
uv run streamlit run src/app.py
