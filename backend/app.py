import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.models import FencePolygon, GPSPoint
from backend.geofence import point_in_polygon
from backend.database import (
    init_db, store_gps, store_alert, get_alerts,
    get_gps_history, save_fence, load_fence,
)
from config import DEFAULT_FENCE, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LON, DEFAULT_ZOOM

# ── Connected WebSocket clients ──
connected_clients: list[WebSocket] = []

# ── Current fence (in-memory for fast checks) ──
current_fence: list[list[float]] = DEFAULT_FENCE.copy()

# ── Latest node positions ──
latest_positions: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Load fence from DB if available, else use default
    stored = load_fence()
    if stored:
        global current_fence
        current_fence = json.loads(stored)
    yield


app = FastAPI(title="Virtual Fencing", lifespan=lifespan)

# Serve dashboard static files
app.mount("/static", StaticFiles(directory="dashboard"), name="static")


@app.get("/")
async def serve_dashboard():
    return FileResponse("dashboard/index.html")


# ── REST APIs ──

@app.get("/api/config")
async def get_config():
    return {
        "center_lat": DEFAULT_CENTER_LAT,
        "center_lon": DEFAULT_CENTER_LON,
        "zoom": DEFAULT_ZOOM,
        "fence": current_fence,
    }


@app.post("/api/fence")
async def set_fence(fence: FencePolygon):
    global current_fence
    current_fence = fence.vertices
    save_fence(json.dumps(fence.vertices))
    # Notify all connected dashboards
    await broadcast({"type": "fence_updated", "fence": current_fence})
    return {"status": "ok", "fence": current_fence}


@app.get("/api/fence")
async def get_fence():
    return {"fence": current_fence}


@app.get("/api/alerts")
async def api_get_alerts(limit: int = 50):
    return {"alerts": get_alerts(limit)}


@app.get("/api/history/{node_name}")
async def api_get_history(node_name: str, limit: int = 100):
    return {"history": get_gps_history(node_name, limit)}


@app.get("/api/positions")
async def api_get_positions():
    return {"positions": latest_positions}


# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        # Send current state on connect
        await ws.send_json({
            "type": "init",
            "fence": current_fence,
            "positions": latest_positions,
        })
        while True:
            # Keep connection alive; dashboard can send commands here
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        connected_clients.remove(ws)


async def broadcast(message: dict):
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.remove(client)


# ── Called by gateway (simulator or LoRa handler) ──

async def process_gps(node_name: str, lat: float, lon: float):
    """Process an incoming GPS point: store, check fence, alert if needed."""
    inside = point_in_polygon(lat, lon, current_fence)

    store_gps(node_name, lat, lon, inside)

    position_data = {
        "node_name": node_name,
        "lat": lat,
        "lon": lon,
        "inside_fence": inside,
    }
    latest_positions[node_name] = position_data

    # Broadcast GPS update to dashboard
    await broadcast({"type": "gps_update", **position_data})

    # If outside fence → trigger alert
    if not inside:
        store_alert(node_name, lat, lon)
        alert_data = {
            "type": "alert",
            "node_name": node_name,
            "lat": lat,
            "lon": lon,
            "alert_type": "GEOFENCE_BREACH",
        }
        await broadcast(alert_data)
        return {"inside": False, "alert_sent": True}

    return {"inside": True, "alert_sent": False}
