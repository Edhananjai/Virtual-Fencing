#include <SPI.h>
#include <LoRa.h>

#define SS 5
#define RST 14
#define DIO0 2

#define BUTTON 4

volatile bool alertFlag = false;

void IRAM_ATTR buttonISR()
{
  alertFlag = true;
}

void setup()
{
  Serial.begin(9600);

  pinMode(BUTTON, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(BUTTON), buttonISR, FALLING);

  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(433E6))
  {
    Serial.println("LoRa init failed");
    while (1);
  }

  Serial.println("Node B Ready");
}

void loop()
{
  int packetSize = LoRa.parsePacket();

  if (packetSize)
  {
    String msg = LoRa.readString();

    Serial.print("Received: ");
    Serial.println(msg);
  }

  // -------- INTERRUPT ALERT --------
  if (alertFlag)
  {
    Serial.println("Sending ALERT");

    for(int i=0;i<3;i++)
    {
      LoRa.beginPacket();
      LoRa.print("ALERT");
      LoRa.endPacket();
      delay(200);
    }

    alertFlag = false;
  }
}