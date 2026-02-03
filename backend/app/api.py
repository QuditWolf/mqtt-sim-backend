import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_db
from .models import (
    Device, Sensor, SensorReading,
    DeviceResponse, DeviceDetailResponse, DeviceListResponse,
    SensorResponse, SensorHistoryResponse, DeviceHistoryResponse,
    SensorReadingResponse
)
from .websocket import manager

router = APIRouter()


# ============ Device Endpoints ============

@router.get("/devices", response_model=DeviceListResponse, summary="List all devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get a list of all known devices with their sensor counts."""
    # Get total count
    count_query = select(func.count(Device.id))
    total = await db.scalar(count_query) or 0
    
    # Get devices with sensors loaded
    query = (
        select(Device)
        .options(selectinload(Device.sensors))
        .order_by(Device.last_seen.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    devices = result.scalars().all()
    
    return DeviceListResponse(
        devices=[
            DeviceResponse(
                id=d.id,
                device_id=d.device_id,
                imei=d.imei,
                total_active_sensors=d.total_active_sensors,
                temperature=d.temperature,
                humidity=d.humidity,
                power_type=d.power_type.value,
                battery_status=d.battery_status,
                rssi=d.rssi,
                last_seen=d.last_seen,
            )
            for d in devices
        ],
        total=total
    )


@router.get("/devices/{device_id}", response_model=DeviceDetailResponse, summary="Get device details")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a device including all its sensors."""
    query = (
        select(Device)
        .options(selectinload(Device.sensors))
        .where(Device.device_id == device_id)
    )
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceDetailResponse(
        id=device.id,
        device_id=device.device_id,
        imei=device.imei,
        total_active_sensors=device.total_active_sensors,
        temperature=device.temperature,
        humidity=device.humidity,
        power_type=device.power_type.value,
        battery_status=device.battery_status,
        rssi=device.rssi,
        last_seen=device.last_seen,
        sensors=[
            SensorResponse(
                id=s.id,
                sensor_type=s.sensor_type,
                sensor_data=s.sensor_data,
                alarm_low=s.alarm_low,
                alarm_high=s.alarm_high,
                fault_status=s.fault_status,
                last_updated=s.last_updated,
            )
            for s in device.sensors
        ]
    )


@router.get("/devices/{device_id}/sensors", response_model=List[SensorResponse], summary="List sensors for a device")
async def list_device_sensors(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get all sensors associated with a device."""
    query = select(Sensor).where(Sensor.device_id == device_id).order_by(Sensor.sensor_type)
    result = await db.execute(query)
    sensors = result.scalars().all()
    
    if not sensors:
        # Check if device exists
        device_query = select(Device).where(Device.device_id == device_id)
        device = await db.scalar(device_query)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
    
    return [
        SensorResponse(
            id=s.id,
            sensor_type=s.sensor_type,
            sensor_data=s.sensor_data,
            alarm_low=s.alarm_low,
            alarm_high=s.alarm_high,
            fault_status=s.fault_status,
            last_updated=s.last_updated,
        )
        for s in sensors
    ]


@router.get("/devices/{device_id}/history", response_model=DeviceHistoryResponse, summary="Get device history")
async def get_device_history(
    device_id: str,
    start_date: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get historical sensor readings for a device."""
    # Build query conditions
    conditions = [SensorReading.device_id == device_id]
    if start_date:
        conditions.append(SensorReading.recorded_at >= start_date)
    if end_date:
        conditions.append(SensorReading.recorded_at <= end_date)
    if sensor_type:
        conditions.append(SensorReading.sensor_type == sensor_type)
    
    # Get total count
    count_query = select(func.count(SensorReading.id)).where(and_(*conditions))
    total = await db.scalar(count_query) or 0
    
    # Get readings
    query = (
        select(SensorReading)
        .where(and_(*conditions))
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    readings = result.scalars().all()
    
    return DeviceHistoryResponse(
        device_id=device_id,
        readings=[
            SensorReadingResponse(
                id=r.id,
                sensor_type=r.sensor_type,
                value=r.value,
                alarm_low=r.alarm_low,
                alarm_high=r.alarm_high,
                fault_status=r.fault_status,
                temperature=r.temperature,
                humidity=r.humidity,
                battery_status=r.battery_status,
                rssi=r.rssi,
                recorded_at=r.recorded_at,
            )
            for r in readings
        ],
        total=total
    )


# ============ Sensor Endpoints ============

@router.get("/sensors/{sensor_id}", response_model=SensorResponse, summary="Get sensor details")
async def get_sensor(sensor_id: int, db: AsyncSession = Depends(get_db)):
    """Get details of a specific sensor."""
    query = select(Sensor).where(Sensor.id == sensor_id)
    result = await db.execute(query)
    sensor = result.scalar_one_or_none()
    
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    return SensorResponse(
        id=sensor.id,
        sensor_type=sensor.sensor_type,
        sensor_data=sensor.sensor_data,
        alarm_low=sensor.alarm_low,
        alarm_high=sensor.alarm_high,
        fault_status=sensor.fault_status,
        last_updated=sensor.last_updated,
    )


@router.get("/sensors/{sensor_id}/history", response_model=SensorHistoryResponse, summary="Get sensor history")
async def get_sensor_history(
    sensor_id: int,
    start_date: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get historical readings for a specific sensor."""
    # First get the sensor to validate it exists
    sensor_query = select(Sensor).where(Sensor.id == sensor_id)
    sensor = await db.scalar(sensor_query)
    
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Build query conditions
    conditions = [SensorReading.sensor_id == sensor_id]
    if start_date:
        conditions.append(SensorReading.recorded_at >= start_date)
    if end_date:
        conditions.append(SensorReading.recorded_at <= end_date)
    
    # Get total count
    count_query = select(func.count(SensorReading.id)).where(and_(*conditions))
    total = await db.scalar(count_query) or 0
    
    # Get readings
    query = (
        select(SensorReading)
        .where(and_(*conditions))
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    readings = result.scalars().all()
    
    return SensorHistoryResponse(
        sensor_id=sensor_id,
        sensor_type=sensor.sensor_type,
        device_id=sensor.device_id,
        readings=[
            SensorReadingResponse(
                id=r.id,
                sensor_type=r.sensor_type,
                value=r.value,
                alarm_low=r.alarm_low,
                alarm_high=r.alarm_high,
                fault_status=r.fault_status,
                temperature=r.temperature,
                humidity=r.humidity,
                battery_status=r.battery_status,
                rssi=r.rssi,
                recorded_at=r.recorded_at,
            )
            for r in readings
        ],
        total=total
    )


# ============ WebSocket Endpoint ============

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket, device_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time sensor updates.
    
    Connect to receive all updates: ws://host/api/ws/live
    Connect for specific device: ws://host/api/ws/live?device_id=DEV001
    
    Messages from client:
    {"action": "subscribe", "device_id": "DEV001"}
    {"action": "unsubscribe", "device_id": "DEV001"}
    """
    await manager.connect(websocket, device_id)
    
    try:
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action")
                target_device = data.get("device_id")
                
                if action == "subscribe" and target_device:
                    manager.subscribe_to_device(websocket, target_device)
                    await websocket.send_json({"type": "subscribed", "device_id": target_device})
                    
                elif action == "unsubscribe" and target_device:
                    manager.unsubscribe_from_device(websocket, target_device)
                    await websocket.send_json({"type": "unsubscribed", "device_id": target_device})
                    
            except Exception:
                await asyncio.sleep(0.1)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

