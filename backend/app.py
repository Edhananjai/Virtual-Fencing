import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.models import FencePolygon, GPSPoint
from backend.geofence import point_in_polygon
from backend.database import (
    init_db, store_gps, store_alert, get_alerts, clear_alerts, clear_all_data,
    get_gps_history, save_fence, load_fence,
)
from config import DEFAULT_CENTER_LAT, DEFAULT_CENTER_LON, DEFAULT_ZOOM

# ── Connected WebSocket clients ──
connected_clients: list[WebSocket] = []

# ── Current fence (in-memory for fast checks) ──
current_fence: list[list[float]] = []

# ── Monitoring state: fence checking only when True ──
monitoring_active: bool = False

# ── Latest node positions ──
latest_positions: dict[str, dict] = {}

# ── Background gateway task ──
gateway_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Fresh start: clear all previous session data
    clear_all_data()

    # Start the gateway (simulator or LoRa) inside the FastAPI event loop
    global gateway_task
    gateway_task = asyncio.create_task(run_gateway())

    yield

    # Cleanup on shutdown
    if gateway_task:
        gateway_task.cancel()


async def run_gateway():
    """Start the appropriate gateway inside the server's event loop."""
    import sys
    from config import MODE

    mode = MODE
    if "--hardware" in sys.argv:
        mode = "HARDWARE"
    elif "--simulator" in sys.argv:
        mode = "SIMULATOR"

    # Small delay to let the server finish starting
    await asyncio.sleep(1)

    if mode == "HARDWARE":
        from gateway.lora_handler import LoRaHandler
        handler = LoRaHandler(callback=process_gps)
        await handler.start()
    else:
        from gateway.simulator import GPSSimulator
        simulator = GPSSimulator(callback=process_gps)
        await simulator.start()


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
        "monitoring": monitoring_active,
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


@app.post("/api/monitoring/start")
async def start_monitoring():
    global monitoring_active
    if len(current_fence) < 3:
        return {"status": "error", "message": "Draw a fence first (at least 3 points)"}
    monitoring_active = True
    clear_alerts()
    await broadcast({"type": "monitoring_started"})
    return {"status": "ok", "monitoring": True}


@app.post("/api/monitoring/stop")
async def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    await broadcast({"type": "monitoring_stopped"})
    return {"status": "ok", "monitoring": False}


@app.get("/api/monitoring")
async def get_monitoring():
    return {"monitoring": monitoring_active}


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
            "monitoring": monitoring_active,
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
    """Process an incoming GPS point: store, check fence only if monitoring is active."""
    # Check fence only when monitoring is on and fence exists
    if monitoring_active and len(current_fence) >= 3:
        inside = point_in_polygon(lat, lon, current_fence)
    else:
        inside = None  # Not monitoring yet — no fence status

    store_gps(node_name, lat, lon, inside if inside is not None else True)

    position_data = {
        "node_name": node_name,
        "lat": lat,
        "lon": lon,
        "inside_fence": inside,  # None = not monitoring, True/False = monitoring
    }
    latest_positions[node_name] = position_data

    # Broadcast GPS update to dashboard
    await broadcast({"type": "gps_update", **position_data})

    # If monitoring and outside fence → trigger alert
    if inside is False:
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
