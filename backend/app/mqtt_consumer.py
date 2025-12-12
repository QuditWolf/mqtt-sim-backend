import asyncio
import os
import logging
from datetime import datetime
import aiomqtt

from .db import insert_record

LOG = logging.getLogger("mqtt_consumer")

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "devices/telemetry")


def parse_csv_message(payload: str) -> dict:
    parts = [p.strip() for p in payload.split(",")]
    while len(parts) < 21:
        parts.append("")

    return {
        "q0": parts[0],
        "q1": parts[1],
        "q2": parts[2],
        "q3": parts[3],
        "q4": parts[4],
        "q5": parts[5],
        "q6": parts[6],
        "q7": parts[7],
        "q8": parts[8],
        "q9": parts[9],
        "q10": parts[10],
        "q11": parts[11],
        "time": parts[12],
        "date": parts[13],
        "q14": parts[14],
        "q15": parts[15],
        "q16": parts[16],
        "battery": parts[17],
        "q18": parts[18],
        "q19": parts[19],
        "q20": parts[20],
    }


async def start_mqtt_loop(loop):
    LOG.info("Starting MQTT consumer using aiomqtt: %s:%s topic=%s",
             MQTT_HOST, MQTT_PORT, MQTT_TOPIC)

    while True:
        try:
            async with aiomqtt.Client(MQTT_HOST, port=MQTT_PORT) as client:
                LOG.info("Connected to MQTT broker")

                messages = client.messages        # <-- no async with
                await client.subscribe(MQTT_TOPIC)

                async for message in messages:
                    try:
                        payload = message.payload.decode()
                        rec = parse_csv_message(payload)
                        await asyncio.to_thread(insert_record, rec)
                    except Exception as e:
                        LOG.exception("Parsing or DB error: %s", e)

        except Exception as e:
            LOG.error("MQTT error: %s — reconnecting in 5 seconds", e)
            await asyncio.sleep(5)

