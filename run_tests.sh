#!/bin/bash
# Test runner script for Birding Vibing filter tests

set -e

echo "=========================================="
echo "  Birding Vibing Filter Tests"
echo "=========================================="
echo ""

# Ensure dependencies are installed
if command -v uv &> /dev/null; then
    echo "Installing/updating test dependencies with uv..."
    uv sync --extra dev
    echo ""
    echo "Running filter tests..."
    echo ""
    
    # Run tests with uv
    uv run pytest tests/ -v --tb=short
else
    echo "⚠️  uv not found. Please install uv or run: pytest tests/ -v"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo ""
echo "✅ All filter tests completed!"
echo ""
echo "To run with coverage report:"
echo "  pytest tests/ --cov=src --cov-report=html"
echo ""

