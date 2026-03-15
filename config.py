# ──────────────────────────────────────────────
# Virtual Fencing — Configuration
# ──────────────────────────────────────────────

# MODE: "SIMULATOR" (no hardware) or "HARDWARE" (real LoRa on RPi)
MODE = "SIMULATOR"

# ── Map Defaults ──
DEFAULT_CENTER_LAT = 17.387375
DEFAULT_CENTER_LON = 78.490608
DEFAULT_ZOOM = 17

# ── Default Fence (polygon around center, ~100m square) ──
# List of [lat, lon] vertices. Dashboard can override at runtime.
DEFAULT_FENCE = [
    [17.3878, 78.4901],
    [17.3878, 78.4911],
    [17.3869, 78.4911],
    [17.3869, 78.4901],
]

# ── Simulator Settings ──
SIMULATOR_INTERVAL = 2.0        # seconds between fake GPS updates
SIMULATOR_NODE_NAME = "NODE_A"

# ── LoRa Hardware Settings (RPi SX1278 via SPI) ──
LORA_FREQUENCY = 433E6          # 433 MHz
LORA_SPI_BUS = 0
LORA_SPI_DEVICE = 0
LORA_CS_PIN = 8                 # GPIO 8 (CE0)
LORA_RESET_PIN = 25             # GPIO 25
LORA_DIO0_PIN = 24              # GPIO 24

# ── Server Settings ──
HOST = "0.0.0.0"
PORT = 8000

# ── Database ──
DATABASE_PATH = "virtual_fencing.db"
