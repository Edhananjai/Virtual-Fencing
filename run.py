"""
run.py — Single entry point for Virtual Fencing system.

Usage:
    python run.py              (simulator mode — default)
    python run.py --hardware   (hardware mode — real LoRa on RPi)
"""

import sys
import asyncio
import uvicorn
import webbrowser
import threading
from config import MODE, HOST, PORT


def start_server():
    """Run the FastAPI server."""
    uvicorn.run("backend.app:app", host=HOST, port=PORT, log_level="info")


async def start_gateway(mode: str):
    """Start the appropriate gateway (simulator or hardware)."""
    # Import here to avoid import errors when hardware libs aren't installed
    from backend.app import process_gps

    if mode == "HARDWARE":
        from gateway.lora_handler import LoRaHandler
        handler = LoRaHandler(callback=process_gps)
        await handler.start()
    else:
        from gateway.simulator import GPSSimulator
        simulator = GPSSimulator(callback=process_gps)
        await simulator.start()


def run_gateway(mode: str):
    """Run gateway in its own event loop."""
    # Wait a moment for the server to start
    import time
    time.sleep(2)
    asyncio.run(start_gateway(mode))


def main():
    mode = MODE

    # Allow command-line override
    if "--hardware" in sys.argv:
        mode = "HARDWARE"
    elif "--simulator" in sys.argv:
        mode = "SIMULATOR"

    print("=" * 50)
    print("   Virtual Fencing System")
    print(f"   Mode: {mode}")
    print(f"   Dashboard: http://localhost:{PORT}")
    print("=" * 50)

    # Start gateway in a separate thread
    gateway_thread = threading.Thread(target=run_gateway, args=(mode,), daemon=True)
    gateway_thread.start()

    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(3)
        webbrowser.open(f"http://localhost:{PORT}")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Start FastAPI server (this blocks)
    start_server()


if __name__ == "__main__":
    main()
