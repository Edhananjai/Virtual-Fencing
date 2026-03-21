/*
 * LoRa + GPS TRANSMITTER
 * Board  : Arduino UNO
 * Modules: SX1278 433 MHz + NEO-6M GPS
 *
 * Packet sent: "NODE_A,<lat>,<lon>"
 *
 * ── SX1278 Wiring ──────────────────────
 *   SX1278 NSS   → UNO Pin 10
 *   SX1278 RST   → UNO Pin 9
 *   SX1278 DIO0  → UNO Pin 2
 *   SX1278 SCK   → UNO Pin 13
 *   SX1278 MOSI  → UNO Pin 11
 *   SX1278 MISO  → UNO Pin 12
 *   SX1278 VCC   → UNO 3.3V  ← NOT 5V
 *   SX1278 GND   → UNO GND
 *
 * ── NEO-6M GPS Wiring ──────────────────
 *   NEO-6M TX    → UNO Pin 4  (GPS data IN to UNO)
 *   NEO-6M RX    → UNO Pin 3  (UNO data OUT to GPS)
 *   NEO-6M VCC   → UNO 5V
 *   NEO-6M GND   → UNO GND
 * ───────────────────────────────────────
 *
 * Libraries needed (install via Library Manager):
 *   - LoRa       by Sandeep Mistry
 *   - TinyGPS++  by Mikal Hart
 */

#include <SPI.h>
#include <LoRa.h>
#include <TinyGPS++.h>
#include <SoftwareSerial.h>

// ── LoRa Pins ──
#define LORA_SS   10
#define LORA_RST   9
#define LORA_DIO0  2

// ── GPS SoftwareSerial Pins ──
#define GPS_RX_PIN  4   // UNO pin 4 ← NEO-6M TX
#define GPS_TX_PIN  3   // UNO pin 3 → NEO-6M RX

// ── Timing ──
#define SEND_INTERVAL 5000  // send every 5 seconds

SoftwareSerial gpsSerial(GPS_RX_PIN, GPS_TX_PIN);
TinyGPSPlus gps;

unsigned long lastSendTime = 0;

void setup()
{
    Serial.begin(9600);
    gpsSerial.begin(9600);

    Serial.println("=== LoRa + GPS Transmitter (UNO) ===");

    // ── Init LoRa ──
    LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
    if (!LoRa.begin(433E6))
    {
        Serial.println("[ERROR] LoRa init failed! Check SX1278 wiring.");
        while (1);
    }
    Serial.println("[OK] LoRa started at 433 MHz");

    // ── GPS startup message ──
    Serial.println("[OK] GPS serial started on pins 3 & 4");
    Serial.println("[INFO] Waiting for GPS satellite fix...");
    Serial.println("[INFO] Take the GPS module near a window or outside.");
    Serial.println("-------------------------------------------");
}

void loop()
{
    // ── Feed all available GPS bytes into TinyGPS++ ──
    while (gpsSerial.available())
    {
        gps.encode(gpsSerial.read());
    }

    unsigned long now = millis();
    if (now - lastSendTime >= SEND_INTERVAL)
    {
        lastSendTime = now;

        if (gps.location.isValid() && gps.location.age() < 2000)
        {
            // ── Valid GPS fix — send real coordinates ──
            double lat = gps.location.lat();
            double lon = gps.location.lng();
            int sats    = gps.satellites.value();

            String packet = "NODE_A," + String(lat, 6) + "," + String(lon, 6);

            LoRa.beginPacket();
            LoRa.print(packet);
            LoRa.endPacket();

            Serial.print("[TX] ");
            Serial.print(packet);
            Serial.print("  (satellites: ");
            Serial.print(sats);
            Serial.println(")");
        }
        else
        {
            // ── No fix yet — report status, do NOT transmit garbage ──
            Serial.print("[WAIT] No GPS fix yet. ");
            Serial.print("Characters received from GPS: ");
            Serial.println(gps.charsProcessed());

            if (gps.charsProcessed() < 10)
            {
                Serial.println("       *** GPS sending NO data — check VCC/GND/TX wiring ***");
            }
            else
            {
                Serial.println("       GPS data arriving, still searching for satellites...");
            }
        }
    }
}
