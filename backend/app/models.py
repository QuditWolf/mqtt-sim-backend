from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel

from .database import Base


# ============ SQLAlchemy ORM Models ============

class PowerType(str, Enum):
    DIRECT = "DIRECT"
    BATTERY = "BATTERY"


class Device(Base):
    """Device table - stores device information."""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    imei: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    power_type: Mapped[PowerType] = mapped_column(SQLEnum(PowerType), default=PowerType.BATTERY)
    battery_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    sensors: Mapped[List["Sensor"]] = relationship("Sensor", back_populates="device", lazy="selectin")

    @property
    def total_active_sensors(self) -> int:
        return len(self.sensors) if self.sensors else 0


class Sensor(Base):
    """Sensor table - stores sensor metadata per device."""
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(50), ForeignKey("devices.device_id"), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # H2, O2, CO, etc.
    sensor_data: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alarm_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alarm_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fault_status: Mapped[int] = mapped_column(Integer, default=0)  # 0=OK, 1=Fault
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="sensors")
    readings: Mapped[List["SensorReading"]] = relationship("SensorReading", back_populates="sensor", lazy="dynamic")

    # Unique constraint for device + sensor_type combination
    __table_args__ = (
        Index("idx_device_sensor_type", "device_id", "sensor_type", unique=True),
    )


class SensorReading(Base):
    """SensorReading table - time-series sensor readings."""
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(Integer, ForeignKey("sensors.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    alarm_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alarm_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fault_status: Mapped[int] = mapped_column(Integer, default=0)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="readings")

    # Indexes for efficient time-series queries
    __table_args__ = (
        Index("idx_sensor_readings_time", "sensor_id", "recorded_at"),
        Index("idx_device_readings_time", "device_id", "recorded_at"),
    )


# ============ Pydantic Schemas (for API responses) ============

class SensorReadingResponse(BaseModel):
    id: int
    sensor_type: str
    value: float
    alarm_low: Optional[float]
    alarm_high: Optional[float]
    fault_status: int
    temperature: Optional[float]
    humidity: Optional[float]
    battery_status: Optional[int]
    rssi: Optional[int]
    recorded_at: datetime

    class Config:
        from_attributes = True


class SensorResponse(BaseModel):
    id: int
    sensor_type: str
    sensor_data: Optional[float]
    alarm_low: Optional[float]
    alarm_high: Optional[float]
    fault_status: int
    last_updated: datetime

    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    imei: str
    total_active_sensors: int
    temperature: Optional[float]
    humidity: Optional[float]
    power_type: str
    battery_status: Optional[int]
    rssi: Optional[int]
    last_seen: datetime

    class Config:
        from_attributes = True


class DeviceDetailResponse(DeviceResponse):
    sensors: List[SensorResponse]


class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]
    total: int


class SensorHistoryResponse(BaseModel):
    sensor_id: int
    sensor_type: str
    device_id: str
    readings: List[SensorReadingResponse]
    total: int


class DeviceHistoryResponse(BaseModel):
    device_id: str
    readings: List[SensorReadingResponse]
    total: int
