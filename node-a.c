#include <SPI.h>
#include <LoRa.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>

#define SS 5
#define RST 14
#define DIO0 2

#define LED 25

TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

void setup()
{
  Serial.begin(9600);
  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);

  pinMode(LED, OUTPUT);

  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(433E6))
  {
    Serial.println("LoRa init failed");
    while (1);
  }

  Serial.println("Node A Ready");
}

void loop()
{

  // -------- READ GPS --------
  while (gpsSerial.available())
  {
    gps.encode(gpsSerial.read());
  }

  float lat = gps.location.lat();
  float lon = gps.location.lng();

  // -------- SEND GPS --------
  LoRa.beginPacket();
  LoRa.print("GPS:");
  LoRa.print(lat,6);
  LoRa.print(",");
  LoRa.print(lon,6);
  LoRa.endPacket();

  Serial.print("Sent GPS: ");
  Serial.print(lat);
  Serial.print(",");
  Serial.println(lon);

  delay(100);

  // -------- LISTEN FOR ALERT --------
  unsigned long startTime = millis();

  while (millis() - startTime < 10000)   // 10 sec listening window
  {
    int packetSize = LoRa.parsePacket();

    if (packetSize)
    {
      String msg = LoRa.readString();

      Serial.println(msg);

      if (msg == "ALERT")
      {
        Serial.println("ALERT RECEIVED");

        digitalWrite(LED, HIGH);
        delay(3000);
        digitalWrite(LED, LOW);

        break;
      }
    }
  }
}