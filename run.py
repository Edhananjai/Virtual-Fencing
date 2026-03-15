"""
run.py — Single entry point for Virtual Fencing system.

Usage:
    python run.py              (simulator mode — default)
    python run.py --hardware   (hardware mode — real LoRa on RPi)
"""

import sys
import uvicorn
import webbrowser
import threading
from config import MODE, HOST, PORT


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

    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(3)
        webbrowser.open(f"http://localhost:{PORT}")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Start FastAPI server (gateway runs as background task inside it)
    uvicorn.run("backend.app:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
