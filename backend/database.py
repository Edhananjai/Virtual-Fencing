import sqlite3
from datetime import datetime, timezone
from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gps_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            inside_fence INTEGER NOT NULL DEFAULT 1,
            timestamp TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            alert_type TEXT NOT NULL DEFAULT 'GEOFENCE_BREACH',
            timestamp TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vertices TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def store_gps(node_name: str, lat: float, lon: float, inside_fence: bool):
    conn = get_connection()
    conn.execute(
        "INSERT INTO gps_history (node_name, lat, lon, inside_fence, timestamp) VALUES (?, ?, ?, ?, ?)",
        (node_name, lat, lon, int(inside_fence), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


def store_alert(node_name: str, lat: float, lon: float, alert_type: str = "GEOFENCE_BREACH"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO alerts (node_name, lat, lon, alert_type, timestamp) VALUES (?, ?, ?, ?, ?)",
        (node_name, lat, lon, alert_type, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


def get_alerts(limit: int = 50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_alerts():
    conn = get_connection()
    conn.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()


def clear_all_data():
    conn = get_connection()
    conn.execute("DELETE FROM gps_history")
    conn.execute("DELETE FROM alerts")
    conn.execute("DELETE FROM fence")
    conn.commit()
    conn.close()


def get_gps_history(node_name: str, limit: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM gps_history WHERE node_name = ? ORDER BY id DESC LIMIT ?",
        (node_name, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_fence(vertices_json: str):
    conn = get_connection()
    conn.execute("DELETE FROM fence")
    conn.execute(
        "INSERT INTO fence (vertices, updated_at) VALUES (?, ?)",
        (vertices_json, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


def load_fence():
    conn = get_connection()
    row = conn.execute("SELECT vertices FROM fence ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return row["vertices"]
    return None
