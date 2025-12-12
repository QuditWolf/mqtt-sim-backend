from pydantic import BaseModel
from typing import Optional

class TelemetryLatest(BaseModel):
    id: int
    q3: str
    q4: Optional[str]
    q5: Optional[str]
    q6: Optional[str]
    time: Optional[str]
    date: Optional[str]
    q9: Optional[float]
    q10: Optional[float]
    q11: Optional[float]
    battery: Optional[int]
    received_at: Optional[str]

