# MQTT Device Simulator + FastAPI Backend (Docker)

This repository runs a simple local environment with:

- **Mosquitto** MQTT broker
- **Simulator** that publishes CSV telemetry for multiple devices every second
- **FastAPI backend** that subscribes to MQTT, stores telemetry in SQLite, and exposes HTTP APIs

## Features

- Messages follow CSV format: `q0,q1,q2,q3,...,q20` (21 fields)
- `q3` is treated as `imei` — used as device identifier
- `q8` sensor field kept as `"0.00"` to avoid server-side recompute (per requirement)
- Backend runs an MQTT subscriber in a background task and writes to SQLite
- HTTP API to list devices, get latest device telemetry, and fetch historical entries and searches by project/site/device

## Quick start (Docker Compose)

Requirements: Docker and Docker Compose.

From repository root:

```bash
docker compose up --build

to test that the process is working:
python test.py
```

# MQTT Device Simulator + FastAPI Backend (Dockerized)

This repository provides a full local simulation stack consisting of:

* **MQTT Simulator** generating telemetry for multiple devices
* **Mosquitto MQTT Broker**
* **FastAPI Backend** subscribing to the MQTT topic, parsing messages, storing them in **SQLite**, and exposing APIs

All services run together via **Docker Compose**.

---

## Features

### Simulator

* Simulates any number of devices (`DEVICE_COUNT`)
* Sends CSV telemetry every 1 second (`PUBLISH_INTERVAL`)
* Auto-randomized device values
* Publishes to MQTT broker on topic: `devices/telemetry`

### Backend

* Subscribes to MQTT using asyncio
* Parses and stores CSV fields (q0–q20) in SQLite
* Provides HTTP API endpoints:

| Endpoint                          | Description                     |
| --------------------------------- | ------------------------------- |
| `GET /api/devices`                | List all devices seen so far    |
| `GET /api/devices/{imei}/latest`  | Latest telemetry for device     |
| `GET /api/devices/{imei}/history` | Historical records              |
| `GET /api/search`                 | Filter by project, site, device |

---

## Architecture Overview

```
+-------------+       MQTT        +-------------+        SQLite        +-----------+
| Simulator   |  ---> 1883 ---->  |  Mosquitto  |  ---> backend ---->  |  DB File  |
| (multiple)  |                   |   Broker    |                     | devices.db|
+-------------+                   +-------------+                     +-----------+
                                          |
                                          v
                                    FastAPI API
                                      localhost:8000
```

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/mqtt-sim-backend.git
cd mqtt-sim-backend
```

### 2. Start the stack

```bash
docker compose up --build
```

### 3. Access the API

Open:

```
http://localhost:8000/docs
```

---

## Environment Variables

Copy `.env.example` → `.env` in both `backend/` and `simulator/`.

### Simulator

| Variable           | Description              |
| ------------------ | ------------------------ |
| `MQTT_HOST`        | Broker hostname          |
| `MQTT_PORT`        | MQTT port                |
| `MQTT_TOPIC`       | Publish topic            |
| `DEVICE_COUNT`     | How many virtual devices |
| `PUBLISH_INTERVAL` | Seconds between messages |

### Backend

| Variable      | Description         |
| ------------- | ------------------- |
| `SQLITE_PATH` | SQLite DB file path |
| `MQTT_HOST`   | Broker host         |
| `MQTT_TOPIC`  | Subscribe topic     |

---

## Example Telemetry Message

```
*,11,1001,867950076170867,123456,AGRAI00,100,2001,0.00,21.0,40.0,6.22,12:00:00,01/01/25,31,1,133,14,100,0,0
```

Field 3 (`q3`) is used as `imei`.

---

## Stopping Services

```bash
docker compose down
```

To clear database and Mosquitto persistence:

```bash
rm -rf mosquitto/data/*
rm -rf backend/app/data/*
```

---

## Roadmap (optional improvements)

* Switch from SQLite → PostgreSQL
* Add authentication on FastAPI routes
* Wrap MQTT consumer in supervisor for auto-restart
* Add Grafana dashboard integration

---

