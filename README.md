# MQTT Sensor Telemetry Backend

Backend for real-time sensor data with MQTT, PostgreSQL, and WebSocket support.

## Features

- **Device & Sensor Hierarchy**: Devices contain multiple sensors (up to 16 types)
- **Real-time Updates**: WebSocket endpoint for live sensor data streaming
- **Historical Data**: REST APIs with date filtering and pagination
- **PostgreSQL**: Scalable time-series storage with connection pooling

## Architecture

```
+-------------+       MQTT        +-------------+        PostgreSQL       
| Simulator   |  ---> 1883 --->   |  Mosquitto  |  ---> backend --->  [DB]
+-------------+                   +-------------+                     
                                        |
                                        v
                                  FastAPI API
                                  localhost:8000
                                        |
                                        v
                                   WebSocket
                                   /ws/live
```

## Quick Start

```bash
# Start all services
docker compose up --build

# Access API docs
open http://localhost:8000/docs
```

## MQTT Payload Format

Each sensor sends a CSV message:
```
*,<status>,<device_id>,<imei>,<sensor_type>,<sensor_data>,<alarm_low>,<alarm_high>,<fault_status>,<temp>,<humidity>,<power_type>,<battery>,<rssi>,<time>,<date>
```

Example:
```
*,11,DEV001,867950076170867,H2,25.5,10.0,50.0,0,28.5,65.2,BATTERY,85,28,14:30:00,20/12/24
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/devices` | List all devices |
| `GET /api/devices/{device_id}` | Device details + sensors |
| `GET /api/devices/{device_id}/sensors` | List sensors |
| `GET /api/devices/{device_id}/history` | Device historical data |
| `GET /api/sensors/{sensor_id}/history` | Sensor historical data |
| `WS /api/ws/live` | Real-time WebSocket |

## WebSocket Usage

Connect to `ws://host:8000/api/ws/live` to receive real-time updates.

**Subscribe to specific device:**
```json
{"action": "subscribe", "device_id": "DEV001"}
```

**Receive sensor updates:**
```json
{
  "type": "sensor_update",
  "device_id": "DEV001",
  "sensor_type": "H2",
  "data": {...}
}
```

## Sensor Types

H2, O2, CO, CH4, NH3, CL2, SO2, NO2, LEL, VOC, CO2, H2S, O3, PH3, HCN, HCL

## Environment Variables

### Backend (.env)
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `MQTT_HOST` | MQTT broker hostname |
| `MQTT_PORT` | MQTT broker port |
| `MQTT_TOPIC` | Topic to subscribe to |

### Simulator (.env)
| Variable | Description |
|----------|-------------|
| `DEVICE_COUNT` | Number of virtual devices |
| `SENSORS_PER_DEVICE` | Sensors per device (max 16) |
| `PUBLISH_INTERVAL` | Seconds between messages |

## Stopping Services

```bash
docker compose down

# Clear data
docker compose down -v
```
