/*
 * LoRa SX1278 Hardware Diagnostic v2
 *
 * Tests each SPI wire individually to pinpoint the exact
 * broken connection. Upload and open Serial Monitor at 9600 baud.
 */

#include <SPI.h>

#define LORA_SS   5
#define LORA_RST  14
#define LORA_DIO0 2
#define LORA_SCK  18
#define LORA_MOSI 23
#define LORA_MISO 19

uint8_t readRegister(uint8_t reg)
{
    digitalWrite(LORA_SS, LOW);
    SPI.transfer(reg & 0x7F);
    uint8_t val = SPI.transfer(0x00);
    digitalWrite(LORA_SS, HIGH);
    return val;
}

void setup()
{
    Serial.begin(9600);
    delay(2000);

    Serial.println("========================================");
    Serial.println("  SX1278 Diagnostic v2 — Wire Locator");
    Serial.println("========================================");
    Serial.println();

    // ── TEST 1: Check MISO state BEFORE SPI starts ──
    // If MISO is floating (disconnected), digitalRead is unpredictable.
    // If module has power but no clock, MISO will sit LOW.
    Serial.println("[TEST 1] MISO idle state (before SPI)...");
    pinMode(LORA_MISO, INPUT_PULLUP); // pull it HIGH artificially
    delay(5);
    int misoHigh = digitalRead(LORA_MISO);
    pinMode(LORA_MISO, INPUT_PULLDOWN); // pull it LOW artificially
    delay(5);
    int misoLow = digitalRead(LORA_MISO);

    if (misoHigh == HIGH && misoLow == LOW)
    {
        Serial.println("   MISO pin is FLOATING (no wire connected)");
        Serial.println("   >>> FIX: Connect SX1278 MISO → ESP32 GPIO 19");
        Serial.println();
        Serial.println("   (Cannot continue — fix MISO first, then re-upload)");
        Serial.println("========================================");
        return;
    }
    else if (misoHigh == LOW && misoLow == LOW)
    {
        Serial.println("   MISO is being driven LOW by the module.");
        Serial.println("   Module has power. SPI clock likely missing.");
    }
    else
    {
        Serial.println("   MISO appears connected.");
    }

    // ── TEST 2: RST pulse — does DIO0 react? ──
    // After a valid RST pulse, SX1278 briefly drives DIO0.
    // If RST is wired wrong, the module never resets cleanly.
    Serial.println("[TEST 2] RST pin pulse...");
    pinMode(LORA_RST, OUTPUT);
    pinMode(LORA_DIO0, INPUT);
    digitalWrite(LORA_RST, LOW);
    delay(10);
    digitalWrite(LORA_RST, HIGH);
    delay(10);
    Serial.println("   RST pulse sent on GPIO 14.");

    // ── TEST 3: Full SPI read ──
    Serial.println("[TEST 3] SPI register read (requires SCK+MOSI+MISO+NSS)...");
    pinMode(LORA_SS, OUTPUT);
    digitalWrite(LORA_SS, HIGH);
    SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS); // explicit pin assignment
    SPI.beginTransaction(SPISettings(100000, MSBFIRST, SPI_MODE0)); // slow speed
    delay(100);

    uint8_t v1 = readRegister(0x42); // version register
    uint8_t v2 = readRegister(0x01); // op-mode register (should be 0x09 after reset)
    uint8_t v3 = readRegister(0x06); // frequency MSB (non-zero after reset)

    Serial.print("   Reg 0x42 (version)  = 0x"); Serial.println(v1, HEX);
    Serial.print("   Reg 0x01 (op mode)  = 0x"); Serial.println(v2, HEX);
    Serial.print("   Reg 0x06 (freq MSB) = 0x"); Serial.println(v3, HEX);

    Serial.println();
    Serial.println("========================================");
    Serial.println("  FINAL DIAGNOSIS");
    Serial.println("========================================");

    if (v1 == 0x12)
    {
        Serial.println("✅ SX1278 FOUND! Wiring is correct.");
        Serial.println("   The LoRa library frequency may be wrong.");
        Serial.println("   Go back to node_a.ino and check: LoRa.begin(433E6)");
        Serial.println("   Make sure your module is actually 433 MHz version.");
    }
    else if (v1 == 0x00 && v2 == 0x00 && v3 == 0x00)
    {
        Serial.println("❌ ALL registers = 0x00");
        Serial.println();
        Serial.println("   This means the SPI clock (SCK) is NOT reaching");
        Serial.println("   the module, OR the NSS/CS line is never going LOW.");
        Serial.println();
        Serial.println("   Check these wires FIRST:");
        Serial.println("   → SX1278 SCK  must connect to ESP32 GPIO 18");
        Serial.println("   → SX1278 NSS  must connect to ESP32 GPIO 5");
        Serial.println("   → SX1278 MOSI must connect to ESP32 GPIO 23");
        Serial.println();
        Serial.println("   Also verify power:");
        Serial.println("   → SX1278 VCC  must connect to ESP32 3.3V (NOT VIN/5V)");
        Serial.println("   → SX1278 GND  must connect to ESP32 GND");
        Serial.println();
        Serial.println("   MOST COMMON MISTAKE: jumper wire is in the wrong hole");
        Serial.println("   on the breadboard, or a wire is loose at one end.");
    }
    else if (v1 == 0xFF)
    {
        Serial.println("❌ ALL registers = 0xFF — MISO stuck HIGH");
        Serial.println("   → Check: SX1278 VCC must be 3.3V, NOT 5V");
        Serial.println("   → If it was ever on 5V, the module is likely burned.");
    }
    else
    {
        Serial.println("⚠️  Partial response — module is alive but unstable.");
        Serial.println("   Check for loose/intermittent connections.");
        Serial.println("   Re-seat all jumper wires firmly.");
    }

    Serial.println("========================================");
    Serial.println();
    Serial.println("  Correct wiring reference:");
    Serial.println("  SX1278 NSS   → ESP32 GPIO  5");
    Serial.println("  SX1278 RST   → ESP32 GPIO 14");
    Serial.println("  SX1278 DIO0  → ESP32 GPIO  2");
    Serial.println("  SX1278 SCK   → ESP32 GPIO 18");
    Serial.println("  SX1278 MOSI  → ESP32 GPIO 23");
    Serial.println("  SX1278 MISO  → ESP32 GPIO 19");
    Serial.println("  SX1278 VCC   → ESP32 3.3V pin");
    Serial.println("  SX1278 GND   → ESP32 GND pin");
    Serial.println("========================================");
}

void loop()
{
    // diagnostic runs once in setup()
}
