"""
GPS Simulator — generates fake GPS data that mimics an animal moving around.
The animal walks in a pattern that sometimes crosses the fence boundary,
so you can test geofence alerts without hardware.
"""

import asyncio
import math
import random
from config import (
    DEFAULT_CENTER_LAT, DEFAULT_CENTER_LON,
    SIMULATOR_INTERVAL, SIMULATOR_NODE_NAME
)


class GPSSimulator:
    def __init__(self, callback):
        """
        callback: async function(node_name, lat, lon) called each tick.
        """
        self.callback = callback
        self.node_name = SIMULATOR_NODE_NAME
        self.center_lat = DEFAULT_CENTER_LAT
        self.center_lon = DEFAULT_CENTER_LON
        self.angle = 0.0
        self.radius = 0.0004  # ~40m — starts inside a ~100m fence
        self.running = False

    async def start(self):
        self.running = True
        print(f"[SIMULATOR] Started — emitting GPS as '{self.node_name}' every {SIMULATOR_INTERVAL}s")

        while self.running:
            # Move in a slowly expanding/contracting circle with randomness
            self.angle += 0.15 + random.uniform(-0.05, 0.05)

            # Radius oscillates: sometimes inside, sometimes outside the fence
            self.radius += random.uniform(-0.00005, 0.00006)
            self.radius = max(0.0001, min(self.radius, 0.0008))

            lat = self.center_lat + self.radius * math.sin(self.angle)
            lon = self.center_lon + self.radius * math.cos(self.angle)

            # Add small noise
            lat += random.uniform(-0.00001, 0.00001)
            lon += random.uniform(-0.00001, 0.00001)

            lat = round(lat, 6)
            lon = round(lon, 6)

            print(f"[SIMULATOR] {self.node_name} → {lat}, {lon}")

            await self.callback(self.node_name, lat, lon)
            await asyncio.sleep(SIMULATOR_INTERVAL)

    def stop(self):
        self.running = False
        print("[SIMULATOR] Stopped")
