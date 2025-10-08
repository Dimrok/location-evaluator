#!/bin/bash

# Multi-City POI Extraction Launch Script
# This script runs the extraction for all French cities

echo "=========================================="
echo "Multi-City POI Grid Extraction"
echo "=========================================="
echo "Cities: Paris, Lille, Bordeaux, Strasbourg, Toulouse"
echo "Cores: 20 (leaving 4 for system)"
echo "Grid: 250m spacing"
echo "=========================================="

# Check if Python script exists
if [ ! -f "extract_city_grid.py" ]; then
    echo "Error: extract_city_grid.py not found!"
    exit 1
fi

# Create data directory
mkdir -p data

# Make script executable
chmod +x extract_city_grid.py

# Run the extraction
echo "Starting extraction at $(date)"
echo "Logs will be saved to extraction.log"
echo ""

python3 extract_city_grid.py

echo ""
echo "=========================================="
echo "Extraction completed at $(date)"
echo "=========================================="
echo "Check data/ directory for results:"
ls -la data/
echo ""
echo "Check extraction.log for detailed logs"
