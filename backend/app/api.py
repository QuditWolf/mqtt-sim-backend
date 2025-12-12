from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from . import db
from .models import TelemetryLatest

router = APIRouter()

@router.get("/devices", summary="List known devices")
async def list_devices():
    return db.fetch_devices()

@router.get("/devices/{imei}/latest", response_model=TelemetryLatest)
async def device_latest(imei: str):
    row = db.fetch_latest_by_imei(imei)
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    return row

@router.get("/devices/{imei}/history")
async def device_history(imei: str, limit: int = Query(100, ge=1, le=10000)):
    return db.query_history(imei=imei, limit=limit)

@router.get("/search")
async def search(project: Optional[str] = None, site: Optional[str] = None, device: Optional[str] = None, limit: int = 100):
    return db.query_history(project=project, site=site, device=device, limit=limit)

