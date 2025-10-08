#!/bin/bash

# Build and run the API
echo "Building API Docker image..."
docker compose -f docker-compose.api.yml build

echo "Starting API server..."
docker compose -f docker-compose.api.yml up -d

echo "API is running on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo ""
echo "Test with:"
echo "curl -X POST 'http://localhost:8000/score-location' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"latitude\": 48.8625, \"longitude\": 2.3472}'"
