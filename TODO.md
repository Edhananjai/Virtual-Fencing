# Virtual Fencing — Project TODO & Hardware Wiring Guide

## Project Overview
A virtual fencing system that tracks animal GPS locations via LoRa (SX1278) and triggers alerts (buzzer + dashboard notification) when an animal crosses a configurable polygon geofence.

**Architecture:** ESP32 (Animal Node) → LoRa SX1278 → Raspberry Pi (Gateway + Backend + Dashboard)

---

## PHASE 1: SOFTWARE BUILD (No Hardware Needed)
> Everything runs in **simulator mode** on your PC/laptop.

### Step 1: Project Config (`config.py`)
- [x] Default map center: 17.387375, 78.490608 (Hyderabad)
- [x] Mode toggle: `SIMULATOR` vs `HARDWARE`
- [x] LoRa serial port config (placeholder for RPi)
- [x] Default polygon fence (square around center point)

### Step 2: Backend Server (`backend/`)
- [x] `models.py` — Data structures for GPS point, node, alert, fence
- [x] `database.py` — SQLite setup, store GPS history, alerts, fence polygons
- [x] `geofence.py` — Ray-casting point-in-polygon algorithm
- [x] `app.py` — FastAPI server with:
  - REST API: get/set fence, get node positions, get alert history
  - WebSocket: live GPS stream + real-time alerts to dashboard

### Step 3: Gateway Layer (`gateway/`)
- [x] `simulator.py` — Generates fake GPS data (node name + lat/lon) that walks around the fence boundary, occasionally going outside to trigger alerts
- [x] `lora_handler.py` — Reads real LoRa packets from SX1278 via SPI on RPi, sends ALERT back over LoRa. **Used only in HARDWARE mode.**

### Step 4: Web Dashboard (`dashboard/`)
- [x] `index.html` — Single page with map, controls, alert panel
- [x] `js/map.js` — Leaflet.js map, draw/edit fence polygon by clicking, show animal marker
- [x] `js/app.js` — WebSocket client, alert notifications, real-time updates
- [x] `css/style.css` — Clean dark UI

### Step 5: ESP32 Firmware (`firmware/node_a.ino`)
- [x] Updated packet format: `NODE_A,<lat>,<lon>`
- [x] Buzzer support on GPIO (activate on ALERT)
- [x] LED blink on ALERT
- [x] Listen for ALERT after each GPS send

### Step 6: Launcher (`run.py`)
- [x] Single entry point: `python run.py`
- [x] Starts FastAPI server + simulator (or LoRa handler in HW mode)
- [x] Opens dashboard in browser

### Step 7: Test End-to-End
- [x] Run `python run.py` — simulator generates GPS
- [x] Dashboard shows map with animal moving
- [x] Draw a fence on the map
- [x] Animal crosses fence → alert on dashboard + "ALERT sent" in logs
- [x] Verify alert history in dashboard

---

## PHASE 2: HARDWARE WIRING (When Hardware Arrives)

### What You Need
| Component          | Qty | Purpose                     |
|--------------------|-----|-----------------------------|
| ESP32 Dev Board    | 1   | Animal node (GPS + LoRa TX) |
| SX1278 LoRa Module | 2   | One for ESP32, one for RPi  |
| NEO-6M GPS Module  | 1   | GPS on animal node          |
| Active Buzzer      | 1   | Alert sound on animal node  |
| LED + 220Ω Resistor| 1   | Visual alert on animal node |
| Raspberry Pi 3/4   | 1   | Base station                |
| Push Button (optional) | 1 | Manual alert (testing)    |
| Jumper Wires       | —   | Connections                 |
| Breadboard         | 1-2 | Prototyping                 |

### Wiring: ESP32 + SX1278 LoRa + GPS + Buzzer

```
ESP32 Pin    →  SX1278 LoRa
─────────────────────────────
GPIO 5  (SS)    →  NSS
GPIO 14 (RST)   →  RESET
GPIO 2  (DIO0)  →  DIO0
GPIO 18 (SCK)   →  SCK
GPIO 23 (MOSI)  →  MOSI
GPIO 19 (MISO)  →  MISO
3.3V            →  VCC
GND             →  GND

ESP32 Pin    →  NEO-6M GPS
─────────────────────────────
GPIO 16 (RX)    →  TX
GPIO 17 (TX)    →  RX
3.3V            →  VCC
GND             →  GND

ESP32 Pin    →  Buzzer
─────────────────────────────
GPIO 26         →  + (positive)
GND             →  - (negative)

ESP32 Pin    →  LED
─────────────────────────────
GPIO 25         →  Anode (+) via 220Ω resistor
GND             →  Cathode (-)
```

### Wiring: Raspberry Pi + SX1278 LoRa

```
RPi Pin         →  SX1278 LoRa
─────────────────────────────
GPIO 8  (CE0/SPI0_CS) →  NSS
GPIO 25              →  RESET
GPIO 24              →  DIO0
GPIO 11 (SPI0_SCLK)  →  SCK
GPIO 10 (SPI0_MOSI)  →  MOSI
GPIO 9  (SPI0_MISO)  →  MISO
3.3V                 →  VCC
GND                  →  GND
```

### Steps to Switch from Simulator to Hardware

1. **Flash ESP32**: Open `firmware/node_a.ino` in Arduino IDE / PlatformIO → Upload to ESP32
2. **Enable SPI on RPi**: `sudo raspi-config` → Interface Options → SPI → Enable
3. **Install RPi dependencies**: `pip install spidev RPi.GPIO`
4. **Edit `config.py`**: Change `MODE = "SIMULATOR"` to `MODE = "HARDWARE"`
5. **Run**: `python run.py` — now reads real LoRa packets instead of simulator
6. **That's it!** Dashboard, geofencing, alerts — all work the same.

---

## FILE STRUCTURE
```
Virtual Fencing/
├── config.py                ← Settings (mode, map center, LoRa config)
├── run.py                   ← Entry point: python run.py
├── requirements.txt         ← Python dependencies
├── TODO.md                  ← This file
│
├── backend/
│   ├── __init__.py
│   ├── app.py               ← FastAPI server + WebSocket
│   ├── geofence.py          ← Point-in-polygon algorithm
│   ├── database.py          ← SQLite operations
│   └── models.py            ← Pydantic data models
│
├── gateway/
│   ├── __init__.py
│   ├── simulator.py         ← Fake GPS data generator
│   └── lora_handler.py      ← Real SX1278 LoRa on RPi
│
├── dashboard/
│   ├── index.html           ← Web UI
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js           ← WebSocket client + alerts
│       └── map.js           ← Leaflet map + fence drawing
│
├── firmware/
│   └── node_a.ino           ← Updated ESP32 firmware
│
├── node-a.c                 ← Original (reference)
└── node-b.c                 ← Original (reference)
```
