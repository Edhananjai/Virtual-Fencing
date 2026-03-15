"""
LoRa Hardware Handler — communicates with SX1278 module on Raspberry Pi via SPI.
This file is ONLY used when MODE = "HARDWARE" in config.py.

When hardware is ready:
1. Wire SX1278 to RPi per TODO.md wiring diagram
2. pip install spidev RPi.GPIO
3. Set MODE = "HARDWARE" in config.py
4. Run: python run.py
"""

import asyncio

try:
    import spidev
    import RPi.GPIO as GPIO
    HW_AVAILABLE = True
except ImportError:
    HW_AVAILABLE = False

from config import (
    LORA_FREQUENCY, LORA_SPI_BUS, LORA_SPI_DEVICE,
    LORA_CS_PIN, LORA_RESET_PIN, LORA_DIO0_PIN,
)

# SX1278 Register addresses
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_TX_BASE = 0x0E
REG_FIFO_RX_BASE = 0x0F
REG_FIFO_RX_CURRENT = 0x10
REG_IRQ_FLAGS = 0x12
REG_RX_NB_BYTES = 0x13
REG_PAYLOAD_LENGTH = 0x22
REG_VERSION = 0x42

# Modes
MODE_SLEEP = 0x00
MODE_STDBY = 0x01
MODE_TX = 0x03
MODE_RX_CONTINUOUS = 0x05
MODE_LONG_RANGE = 0x80

# IRQ flags
IRQ_RX_DONE = 0x40
IRQ_TX_DONE = 0x08


class LoRaHandler:
    def __init__(self, callback):
        """
        callback: async function(node_name, lat, lon) called when a valid packet is received.
        """
        if not HW_AVAILABLE:
            raise RuntimeError(
                "LoRa hardware libraries not available. "
                "Install with: pip install spidev RPi.GPIO\n"
                "Or use MODE = 'SIMULATOR' in config.py"
            )

        self.callback = callback
        self.spi = None
        self.running = False

    def _spi_write(self, register, value):
        self.spi.xfer2([register | 0x80, value])

    def _spi_read(self, register):
        return self.spi.xfer2([register & 0x7F, 0x00])[1]

    def _set_mode(self, mode):
        self._spi_write(REG_OP_MODE, MODE_LONG_RANGE | mode)

    def _set_frequency(self, freq):
        frf = int((freq / 32e6) * (2**19))
        self._spi_write(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._spi_write(REG_FRF_MID, (frf >> 8) & 0xFF)
        self._spi_write(REG_FRF_LSB, frf & 0xFF)

    def setup(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LORA_RESET_PIN, GPIO.OUT)
        GPIO.setup(LORA_DIO0_PIN, GPIO.IN)

        # Reset the module
        GPIO.output(LORA_RESET_PIN, GPIO.LOW)
        import time
        time.sleep(0.01)
        GPIO.output(LORA_RESET_PIN, GPIO.HIGH)
        time.sleep(0.01)

        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(LORA_SPI_BUS, LORA_SPI_DEVICE)
        self.spi.max_speed_hz = 5000000

        # Verify module
        version = self._spi_read(REG_VERSION)
        if version != 0x12:
            raise RuntimeError(f"SX1278 not found (version: 0x{version:02X})")

        # Configure
        self._set_mode(MODE_SLEEP)
        self._set_frequency(LORA_FREQUENCY)
        self._spi_write(REG_FIFO_TX_BASE, 0x00)
        self._spi_write(REG_FIFO_RX_BASE, 0x00)
        self._set_mode(MODE_STDBY)

        print(f"[LORA] SX1278 initialized at {LORA_FREQUENCY / 1e6} MHz")

    def _receive_packet(self):
        irq = self._spi_read(REG_IRQ_FLAGS)
        if irq & IRQ_RX_DONE:
            # Clear IRQ
            self._spi_write(REG_IRQ_FLAGS, IRQ_RX_DONE)

            # Read payload
            current_addr = self._spi_read(REG_FIFO_RX_CURRENT)
            self._spi_write(REG_FIFO_ADDR_PTR, current_addr)
            nb_bytes = self._spi_read(REG_RX_NB_BYTES)

            payload = bytearray()
            for _ in range(nb_bytes):
                payload.append(self._spi_read(REG_FIFO))

            return payload.decode("utf-8", errors="ignore")
        return None

    def send_packet(self, data: str):
        self._set_mode(MODE_STDBY)
        self._spi_write(REG_FIFO_ADDR_PTR, 0x00)

        payload = data.encode("utf-8")
        for byte in payload:
            self._spi_write(REG_FIFO, byte)

        self._spi_write(REG_PAYLOAD_LENGTH, len(payload))
        self._set_mode(MODE_TX)

        # Wait for TX done
        while not (self._spi_read(REG_IRQ_FLAGS) & IRQ_TX_DONE):
            pass
        self._spi_write(REG_IRQ_FLAGS, IRQ_TX_DONE)
        print(f"[LORA] Sent: {data}")

    def _parse_packet(self, raw: str):
        """Parse 'NODE_A,17.387375,78.490608' format."""
        try:
            parts = raw.strip().split(",")
            if len(parts) == 3:
                node_name = parts[0]
                lat = float(parts[1])
                lon = float(parts[2])
                return node_name, lat, lon
        except (ValueError, IndexError):
            pass
        return None

    async def start(self):
        self.setup()
        self.running = True
        self._set_mode(MODE_RX_CONTINUOUS)
        print("[LORA] Listening for packets...")

        while self.running:
            raw = self._receive_packet()
            if raw:
                print(f"[LORA] Received: {raw}")
                parsed = self._parse_packet(raw)
                if parsed:
                    node_name, lat, lon = parsed
                    result = await self.callback(node_name, lat, lon)

                    # If animal is outside fence, send ALERT back
                    if result and result.get("alert_sent"):
                        self.send_packet("ALERT")
                        self._set_mode(MODE_RX_CONTINUOUS)

            await asyncio.sleep(0.1)

    def stop(self):
        self.running = False
        if self.spi:
            self.spi.close()
        if HW_AVAILABLE:
            GPIO.cleanup()
        print("[LORA] Stopped")
