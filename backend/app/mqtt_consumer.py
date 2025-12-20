import asyncio
import os
import logging
from datetime import datetime
import aiomqtt
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import get_db_context
from .models import Device, Sensor, SensorReading, PowerType
from .websocket import manager

LOG = logging.getLogger("mqtt_consumer")

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "devices/telemetry")


def parse_sensor_message(payload: str) -> dict:
    """
    Parse new sensor message format:
    *,<status>,<device_id>,<imei>,<sensor_type>,<sensor_data>,<alarm_low>,<alarm_high>,
    <fault_status>,<temp>,<humidity>,<power_type>,<battery>,<rssi>,<time>,<date>
    """
    parts = [p.strip() for p in payload.split(",")]
    
    # Ensure we have at least 16 fields
    while len(parts) < 16:
        parts.append("")
    
    # Parse power type
    power_type_str = parts[11].upper() if parts[11] else "BATTERY"
    power_type = PowerType.DIRECT if power_type_str == "DIRECT" else PowerType.BATTERY
    
    # Parse date and time to datetime
    try:
        time_str = parts[14]  # HH:MM:SS
        date_str = parts[15]  # DD/MM/YY
        if time_str and date_str:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %H:%M:%S")
        else:
            dt = datetime.utcnow()
    except ValueError:
        dt = datetime.utcnow()
    
    return {
        "start_marker": parts[0],
        "status": int(parts[1]) if parts[1].isdigit() else 0,
        "device_id": parts[2],
        "imei": parts[3],
        "sensor_type": parts[4],
        "sensor_data": float(parts[5]) if parts[5] else 0.0,
        "alarm_low": float(parts[6]) if parts[6] else 0.0,
        "alarm_high": float(parts[7]) if parts[7] else 0.0,
        "fault_status": int(parts[8]) if parts[8].isdigit() else 0,
        "temperature": float(parts[9]) if parts[9] else None,
        "humidity": float(parts[10]) if parts[10] else None,
        "power_type": power_type,
        "battery_status": int(parts[12]) if parts[12].isdigit() else None,
        "rssi": int(parts[13]) if parts[13].isdigit() else None,
        "recorded_at": dt,
    }


async def process_sensor_data(data: dict):
    """Process parsed sensor data: upsert device, upsert sensor, insert reading."""
    async with get_db_context() as session:
        now = datetime.utcnow()
        
        # 1. Upsert Device
        device_stmt = pg_insert(Device).values(
            device_id=data["device_id"],
            imei=data["imei"],
            temperature=data["temperature"],
            humidity=data["humidity"],
            power_type=data["power_type"],
            battery_status=data["battery_status"],
            rssi=data["rssi"],
            last_seen=now,
            created_at=now,
        ).on_conflict_do_update(
            index_elements=["device_id"],
            set_={
                "temperature": data["temperature"],
                "humidity": data["humidity"],
                "power_type": data["power_type"],
                "battery_status": data["battery_status"],
                "rssi": data["rssi"],
                "last_seen": now,
            }
        )
        await session.execute(device_stmt)
        
        # 2. Upsert Sensor
        sensor_stmt = pg_insert(Sensor).values(
            device_id=data["device_id"],
            sensor_type=data["sensor_type"],
            sensor_data=data["sensor_data"],
            alarm_low=data["alarm_low"],
            alarm_high=data["alarm_high"],
            fault_status=data["fault_status"],
            last_updated=now,
            created_at=now,
        ).on_conflict_do_update(
            index_elements=["device_id", "sensor_type"],
            set_={
                "sensor_data": data["sensor_data"],
                "alarm_low": data["alarm_low"],
                "alarm_high": data["alarm_high"],
                "fault_status": data["fault_status"],
                "last_updated": now,
            }
        ).returning(Sensor.id)
        
        result = await session.execute(sensor_stmt)
        sensor_id = result.scalar_one()
        
        # 3. Insert Sensor Reading (time-series)
        reading = SensorReading(
            sensor_id=sensor_id,
            device_id=data["device_id"],
            sensor_type=data["sensor_type"],
            value=data["sensor_data"],
            alarm_low=data["alarm_low"],
            alarm_high=data["alarm_high"],
            fault_status=data["fault_status"],
            temperature=data["temperature"],
            humidity=data["humidity"],
            battery_status=data["battery_status"],
            rssi=data["rssi"],
            recorded_at=data["recorded_at"],
        )
        session.add(reading)
        
        await session.commit()
        
        # 4. Broadcast to WebSocket clients
        ws_data = {
            "device_id": data["device_id"],
            "imei": data["imei"],
            "sensor_type": data["sensor_type"],
            "sensor_data": data["sensor_data"],
            "alarm_low": data["alarm_low"],
            "alarm_high": data["alarm_high"],
            "fault_status": data["fault_status"],
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "power_type": data["power_type"].value,
            "battery_status": data["battery_status"],
            "rssi": data["rssi"],
            "recorded_at": data["recorded_at"].isoformat(),
        }
        await manager.broadcast_sensor_update(
            data["device_id"],
            data["sensor_type"],
            ws_data
        )


async def start_mqtt_loop(loop):
    """Main MQTT consumer loop - subscribes to broker and processes messages."""
    LOG.info("Starting MQTT consumer using aiomqtt: %s:%s topic=%s",
             MQTT_HOST, MQTT_PORT, MQTT_TOPIC)

    while True:
        try:
            async with aiomqtt.Client(MQTT_HOST, port=MQTT_PORT) as client:
                LOG.info("Connected to MQTT broker")

                messages = client.messages
                await client.subscribe(MQTT_TOPIC)

                async for message in messages:
                    try:
                        payload = message.payload.decode()
                        LOG.debug(f"Received: {payload}")
                        
                        data = parse_sensor_message(payload)
                        
                        # Validate essential fields
                        if not data["device_id"] or not data["sensor_type"]:
                            LOG.warning("Missing device_id or sensor_type, skipping")
                            continue
                        
                        await process_sensor_data(data)
                        
                    except Exception as e:
                        LOG.exception("Parsing or DB error: %s", e)

        except Exception as e:
            LOG.error("MQTT error: %s — reconnecting in 5 seconds", e)
            await asyncio.sleep(5)
