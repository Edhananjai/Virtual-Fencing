/*
 * Virtual Fencing — ESP32 Animal Node Firmware
 * 
 * Hardware: ESP32 + SX1278 LoRa + NEO-6M GPS + Buzzer + LED
 * Packet format sent: "NODE_A,<lat>,<lon>"
 * Listens for: "ALERT" from base station
 *
 * Pin connections — see TODO.md for full wiring diagram.
 */

#include <SPI.h>
#include <LoRa.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>

// ── LoRa Pins ──
#define LORA_SS    5
#define LORA_RST   14
#define LORA_DIO0  2

// ── GPS Serial Pins ──
#define GPS_RX     16
#define GPS_TX     17

// ── Alert Output Pins ──
#define LED_PIN    25
#define BUZZER_PIN 26

// ── Node Identity ──
#define NODE_NAME  "NODE_A"

// ── Timing ──
#define GPS_SEND_INTERVAL 2000    // ms between GPS transmissions
#define ALERT_LISTEN_TIME 8000    // ms to listen for alerts after sending
#define ALERT_DURATION    3000    // ms to buzz/blink on alert

TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

void triggerAlert();

void setup()
{
    Serial.begin(9600);
    gpsSerial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);

    pinMode(LED_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);

    LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

    if (!LoRa.begin(433E6))
    {
        Serial.println("[ERROR] LoRa init failed!");
        while (1)
        {
            digitalWrite(LED_PIN, HIGH);
            delay(200);
            digitalWrite(LED_PIN, LOW);
            delay(200);
        }
    }

    Serial.println("[OK] " NODE_NAME " Ready");
    Serial.println("[OK] LoRa @ 433 MHz");
}

void loop()
{
    // ── 1. Read GPS data ──
    unsigned long gpsStart = millis();
    while (millis() - gpsStart < GPS_SEND_INTERVAL)
    {
        while (gpsSerial.available())
        {
            gps.encode(gpsSerial.read());
        }
    }

    float lat = gps.location.lat();
    float lon = gps.location.lng();

    // ── 2. Send packet: "NODE_A,lat,lon" ──
    String packet = String(NODE_NAME) + "," + String(lat, 6) + "," + String(lon, 6);

    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();

    Serial.print("[TX] ");
    Serial.println(packet);

    // ── 3. Listen for ALERT response ──
    unsigned long listenStart = millis();

    while (millis() - listenStart < ALERT_LISTEN_TIME)
    {
        int packetSize = LoRa.parsePacket();

        if (packetSize)
        {
            String msg = LoRa.readString();
            Serial.print("[RX] ");
            Serial.println(msg);

            if (msg == "ALERT")
            {
                Serial.println("[!!] GEOFENCE BREACH — ALERT TRIGGERED");
                triggerAlert();
                break;
            }
        }
    }
}

void triggerAlert()
{
    unsigned long start = millis();

    while (millis() - start < ALERT_DURATION)
    {
        // Buzzer ON + LED ON
        digitalWrite(BUZZER_PIN, HIGH);
        digitalWrite(LED_PIN, HIGH);
        delay(200);

        // Buzzer OFF + LED OFF
        digitalWrite(BUZZER_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        delay(200);
    }

    // Ensure both are off
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
}
