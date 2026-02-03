#!/bin/bash
# Run the MQTT simulator locally (outside Docker)

set -e

cd "$(dirname "$0")/simulator"

echo "=== Setting up Python virtual environment ==="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "=== Installing dependencies ==="
pip install paho-mqtt python-dotenv

echo "=== Using local MQTT broker ==="
export MQTT_HOST=localhost
export MQTT_PORT=1883
export MQTT_TOPIC=devices/telemetry
export NUM_DEVICES=3
export PUBLISH_INTERVAL=2

echo ""
echo "=== Starting MQTT Simulator ==="
echo "    Publishing to: localhost:1883"
echo "    Topic: devices/telemetry"
echo "    Devices: DEV001, DEV002, DEV003"
echo ""

python simulator.py
