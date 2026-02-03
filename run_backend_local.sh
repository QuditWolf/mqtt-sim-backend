#!/bin/bash
# Run the backend locally (outside Docker)
# This is useful for testing with physical mobile devices

set -e

cd "$(dirname "$0")/backend"

echo "=== Setting up Python virtual environment ==="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Using local environment ==="
cp .env.local .env.active
export $(cat .env.local | grep -v '^#' | xargs)

echo ""
echo "=== Starting Backend Server on 0.0.0.0:8000 ==="
echo "    API: http://192.168.1.60:8000/api"
echo "    WebSocket: ws://192.168.1.60:8000/api/ws/live"
echo ""

# Run on 0.0.0.0 so it's accessible from other devices on the network
# NOTE: Do NOT use --reload flag! It creates separate worker processes where
# MQTT consumer and WebSocket handlers have different ConnectionManager instances,
# causing WebSocket broadcasts to show "0 subscribers".
uvicorn app.main:app --host 0.0.0.0 --port 8000
