from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class GPSPoint(BaseModel):
    node_name: str
    lat: float
    lon: float
    timestamp: Optional[str] = None


class FencePolygon(BaseModel):
    vertices: List[List[float]]  # [[lat, lon], [lat, lon], ...]


class Alert(BaseModel):
    id: Optional[int] = None
    node_name: str
    lat: float
    lon: float
    timestamp: Optional[str] = None
    alert_type: str = "GEOFENCE_BREACH"


class NodeStatus(BaseModel):
    node_name: str
    lat: float
    lon: float
    inside_fence: bool
    timestamp: str
