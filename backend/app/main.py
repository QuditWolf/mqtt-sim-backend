import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from .mqtt_consumer import start_mqtt_loop
from .api import router as api_router
from .database import init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    LOG.info("Initializing database...")
    await init_db()
    
    LOG.info("Starting MQTT consumer...")
    loop = asyncio.get_event_loop()
    mqtt_task = loop.create_task(start_mqtt_loop(loop))
    
    yield
    
    # Shutdown
    LOG.info("Shutting down MQTT consumer...")
    mqtt_task.cancel()
    try:
        await mqtt_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="MQTT Sensor Telemetry Backend",
    description="FastAPI backend for real-time sensor data with MQTT and WebSocket",
    version="2.0.0",
    lifespan=lifespan,
)

# Include API router
app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mqtt-sensor-backend"}
