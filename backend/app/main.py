import asyncio
import logging
import os
from fastapi import FastAPI
from .mqtt_consumer import start_mqtt_loop
from .api import router as api_router
from .db import get_conn
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("backend")

app = FastAPI(title="MQTT Telemetry Backend")

app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    # Launch MQTT consumer background task
    get_conn()
    loop = asyncio.get_event_loop()
    app.state.mqtt_task = loop.create_task(start_mqtt_loop(loop))
    LOG.info("MQTT consumer started")

@app.on_event("shutdown")
async def shutdown_event():
    task = app.state.mqtt_task
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

