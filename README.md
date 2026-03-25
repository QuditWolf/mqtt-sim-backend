# MQTT Sensor Telemetry Backend

Industrial IoT gas sensor telemetry backend — real-time MQTT ingestion, PostgreSQL time-series storage, and WebSocket streaming for multi-device sensor deployments.

---

## Real-World Context

This backend is built for industrial environments that continuously monitor toxic and flammable gas levels. Field devices push CSV-format telemetry over MQTT at configurable intervals, reporting live readings from sensors including H2, CO, CH4, H2S, NH3, CL2, and others.

MQTT is used because it is a low-overhead publish/subscribe protocol designed for constrained field devices operating over unreliable links. The Mosquitto broker decouples devices from the backend: devices publish and disconnect without knowing who is consuming. PostgreSQL handles time-series storage at scale with explicit indexes on `(sensor_id, recorded_at)` and `(device_id, recorded_at)`. The WebSocket endpoint eliminates polling — live dashboards receive a push on every inbound reading.

Each message carries `alarm_low` and `alarm_high` thresholds per sensor type, enabling threshold-based alerting in any consuming client or downstream service.

---

## Architecture

```
Field Devices / Simulator
        |
        | MQTT (CSV payload, port 1883)
        v
  Mosquitto Broker
  (eclipse-mosquitto:2.0, anonymous, persistent)
        |
        | subscribe (aiomqtt, async)
        v
  FastAPI Ingest Service  (port 8000)
        |
        +--[upsert]--> PostgreSQL  (port 5433)
        |              devices / sensors / sensor_readings
        |              connection pool: size=10, overflow=20
        |
        +--[broadcast]--> WebSocket /api/ws/live
                                |
                                v
                     Live monitoring dashboard
                     (per-device subscriptions or global feed)
```

---

## Sensor Types

| Code | Gas | Hazard Class | Typical Range |
|------|-----|--------------|---------------|
| H2   | Hydrogen | Flammable | 0–100 ppm |
| O2   | Oxygen | Asphyxiant (depletion) | 18–23 % |
| CO   | Carbon Monoxide | Toxic | 0–50 ppm |
| CH4  | Methane | Flammable / Explosive | 0–5 % LEL |
| NH3  | Ammonia | Toxic | 0–50 ppm |
| CL2  | Chlorine | Toxic | 0–1 ppm |
| SO2  | Sulphur Dioxide | Toxic | 0–5 ppm |
| NO2  | Nitrogen Dioxide | Toxic | 0–5 ppm |
| LEL  | Lower Explosive Limit | Explosion risk | 0–100 % |
| VOC  | Volatile Organic Compounds | Toxic / Flammable | 0–500 ppb |
| CO2  | Carbon Dioxide | Asphyxiant | 400–2000 ppm |
| H2S  | Hydrogen Sulphide | Toxic | 0–20 ppm |
| O3   | Ozone | Toxic | 0–0.1 ppm |
| PH3  | Phosphine | Toxic / Flammable | 0–1 ppm |
| HCN  | Hydrogen Cyanide | Toxic | 0–10 ppm |
| HCL  | Hydrogen Chloride | Toxic / Corrosive | 0–5 ppm |

---

## MQTT Payload Format

Each sensor reading is published as a single comma-separated message:

```
*,<status>,<device_id>,<imei>,<sensor_type>,<sensor_data>,<alarm_low>,<alarm_high>,<fault_status>,<temp>,<humidity>,<power_type>,<battery>,<rssi>,<time>,<date>
```

**Example:**
```
*,11,DEV001,867950076170867,H2,25.50,10.0,50.0,0,28.5,65.2,BATTERY,85,28,14:30:00,20/12/24
```

**Field breakdown:**

| Field | Description |
|-------|-------------|
| `*` | Start marker (literal asterisk) |
| `status` | Device status code (11 = normal operation) |
| `device_id` | Unique device identifier (e.g. `DEV001`) |
| `imei` | Hardware IMEI (15-digit numeric string) |
| `sensor_type` | Gas type code (H2, CO, CH4, H2S, etc.) |
| `sensor_data` | Current sensor reading (float) |
| `alarm_low` | Low threshold — readings below this trigger low alarm |
| `alarm_high` | High threshold — readings above this trigger high alarm |
| `fault_status` | Sensor fault flag: `0` = OK, `1` = Fault |
| `temp` | Ambient temperature (°C) |
| `humidity` | Ambient relative humidity (%) |
| `power_type` | `BATTERY` or `DIRECT` (mains power) |
| `battery` | Battery level (%, 100 for DIRECT-powered devices) |
| `rssi` | Signal strength (range 5–31) |
| `time` | Timestamp `HH:MM:SS` |
| `date` | Date `DD/MM/YY` |

One MQTT message is published per sensor per publish cycle. A device with 16 sensors publishes 16 messages per interval.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/devices` | List all devices (paginated, ordered by `last_seen`) |
| `GET` | `/api/devices/{device_id}` | Device details + all sensors |
| `GET` | `/api/devices/{device_id}/sensors` | List sensors for a device |
| `GET` | `/api/devices/{device_id}/history` | Time-series readings (filterable by date range and sensor type) |
| `GET` | `/api/sensors/{sensor_id}` | Sensor details |
| `GET` | `/api/sensors/{sensor_id}/history` | Sensor time-series readings |
| `WS`  | `/api/ws/live` | Real-time WebSocket stream |

Interactive docs: `http://localhost:8000/docs`

### WebSocket Protocol

**Connect (global feed — all devices):**
```
ws://localhost:8000/api/ws/live
```

**Connect (filtered to one device):**
```
ws://localhost:8000/api/ws/live?device_id=DEV001
```

**Subscribe/unsubscribe after connecting:**
```json
{"action": "subscribe",   "device_id": "DEV001"}
{"action": "unsubscribe", "device_id": "DEV001"}
```

**Inbound message format:**
```json
{
  "type": "sensor_update",
  "device_id": "DEV001",
  "sensor_type": "H2",
  "data": {
    "device_id": "DEV001",
    "imei": "867950076170867",
    "sensor_type": "H2",
    "sensor_data": 25.5,
    "alarm_low": 10.0,
    "alarm_high": 50.0,
    "fault_status": 0,
    "temperature": 28.5,
    "humidity": 65.2,
    "power_type": "BATTERY",
    "battery_status": 85,
    "rssi": 28,
    "recorded_at": "2024-12-20T14:30:00"
  }
}
```

Connections with no device subscription receive updates for all devices. Connections subscribed to a device receive only that device's updates.

---

## Quick Start

### Docker (recommended)

```bash
# Build and start all services
docker compose up --build

# Verify ingestion
curl http://localhost:8000/api/devices

# Tail live data
wscat -c ws://localhost:8000/api/ws/live
```

Services started: `postgres` (5433), `mosquitto` (1883), `backend` (8000), `simulator`.

**Stop and remove data:**
```bash
docker compose down        # stop, keep volumes
docker compose down -v     # stop and delete DB volume
```

### Bare Metal

**Backend:**
```bash
./run_backend_local.sh
# Reads .env.local, starts uvicorn on 0.0.0.0:8000
# Do NOT use --reload: it forks worker processes causing split ConnectionManager
# instances, which breaks WebSocket broadcasts
```

**Simulator:**
```bash
./run_simulator_local.sh
# Connects to localhost:1883 by default
```

A Mosquitto broker must already be running (e.g. via `docker compose up mosquitto`).

---

## Simulator

The simulator generates realistic telemetry for hardware-free development and load testing. It publishes one MQTT message per sensor per cycle, with physically plausible readings and randomised fault events (2% probability per reading).

**Defaults (configurable via `simulator/.env`):**
- 3 devices
- 16 sensors per device (full gas suite)
- 2-second publish interval

**What one cycle produces:**

```
3 devices × 16 sensors = 48 MQTT messages per cycle
At 2s interval → ~24 readings/second into PostgreSQL
```

Battery-powered devices slowly drain (−1% per cycle with 10% probability), simulating real field behaviour.

**Sample generated message:**
```
*,11,DEV002,491823057164320,CO,18.73,25.0,50.0,0,31.2,58.4,BATTERY,92,17,09:15:32,25/03/26
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/pelectro` | SQLAlchemy async connection string |
| `MQTT_HOST` | `mosquitto` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_TOPIC` | `devices/telemetry` | Topic to subscribe to |

### Simulator (`simulator/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | `mosquitto` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_TOPIC` | `devices/telemetry` | Topic to publish to |
| `DEVICE_COUNT` | `3` | Number of virtual devices |
| `SENSORS_PER_DEVICE` | `16` | Sensors per device (max 16) |
| `PUBLISH_INTERVAL` | `2.0` | Seconds between publish cycles |

---

## Database Schema

Three tables, created automatically on startup:

- **`devices`** — one row per device (`device_id` unique). Updated on every inbound message with latest ambient conditions, battery, and RSSI.
- **`sensors`** — one row per `(device_id, sensor_type)`. Updated with current reading and thresholds.
- **`sensor_readings`** — append-only time-series. Every inbound message appends a row. Indexes on `(sensor_id, recorded_at)` and `(device_id, recorded_at)` support range queries.

The backend upserts devices and sensors on every message and appends to `sensor_readings`, so no schema initialisation is required beyond `docker compose up`.

---

## Notes

- No authentication is configured on the API or MQTT broker (`allow_anonymous true`). Add auth before exposing to an untrusted network.
- The backend runs a single uvicorn worker. `--reload` must not be used in production or local testing — it creates separate processes with independent `ConnectionManager` instances, silently breaking WebSocket broadcasts.
