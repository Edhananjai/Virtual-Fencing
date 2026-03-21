/*
 * LoRa GPS RECEIVER
 * Board  : ESP32
 * Module : SX1278 433 MHz
 *
 * Receives "NODE_A,<lat>,<lon>" packets from the UNO+GPS transmitter.
 *
 * ── SX1278 Wiring ──────────────────────
 *   SX1278 NSS   → ESP32 GPIO 5
 *   SX1278 RST   → ESP32 GPIO 14
 *   SX1278 DIO0  → ESP32 GPIO 2
 *   SX1278 SCK   → ESP32 GPIO 18
 *   SX1278 MOSI  → ESP32 GPIO 23
 *   SX1278 MISO  → ESP32 GPIO 19
 *   SX1278 VCC   → ESP32 3.3V  ← NOT 5V
 *   SX1278 GND   → ESP32 GND
 * ───────────────────────────────────────
 */

#include <SPI.h>
#include <LoRa.h>

#define LORA_SS    5
#define LORA_RST  14
#define LORA_DIO0  2

void setup()
{
    Serial.begin(9600);

    Serial.println("=== LoRa GPS Receiver (ESP32) ===");

    LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

    if (!LoRa.begin(433E6))
    {
        Serial.println("[ERROR] LoRa init failed! Check SX1278 wiring.");
        while (1);
    }

    Serial.println("[OK] LoRa started at 433 MHz");
    Serial.println("[INFO] Waiting for GPS packets from UNO...");
    Serial.println("-------------------------------------------");
}

void loop()
{
    int packetSize = LoRa.parsePacket();

    if (packetSize)
    {
        String received = "";
        while (LoRa.available())
        {
            received += (char)LoRa.read();
        }

        int rssi = LoRa.packetRssi();

        Serial.println("=== Packet Received ===");
        Serial.print("  Raw     : ");
        Serial.println(received);

        // ── Parse "NODE_A,lat,lon" ──
        int firstComma  = received.indexOf(',');
        int secondComma = received.indexOf(',', firstComma + 1);

        if (firstComma > 0 && secondComma > firstComma)
        {
            String nodeName = received.substring(0, firstComma);
            String latStr   = received.substring(firstComma + 1, secondComma);
            String lonStr   = received.substring(secondComma + 1);

            double lat = latStr.toDouble();
            double lon = lonStr.toDouble();

            Serial.print("  Node    : "); Serial.println(nodeName);
            Serial.print("  Lat     : "); Serial.println(lat, 6);
            Serial.print("  Lon     : "); Serial.println(lon, 6);
            Serial.print("  RSSI    : "); Serial.print(rssi); Serial.println(" dBm");

            // Quick sanity check on coordinates
            if (lat == 0.0 && lon == 0.0)
            {
                Serial.println("  [NOTE] Coordinates are 0,0 — GPS may not have a fix yet");
            }
        }
        else
        {
            Serial.println("  [WARN] Packet format not recognised.");
            Serial.print("  RSSI: "); Serial.print(rssi); Serial.println(" dBm");
        }

        Serial.println("-------------------------------------------");
    }
}
