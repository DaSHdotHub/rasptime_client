#!/usr/bin/env python3
"""Detailed RC522 diagnostic"""
import RPi.GPIO as GPIO
import spidev
import time

RST_PIN = 24

print("=== RC522 Diagnostic ===\n")

# Check SPI device
print("1. Checking SPI device...")
try:
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1000000
    print("   SPI0.0 opened successfully")

    # Try to read RC522 version register (0x37)
    # RC522 command: (register << 1) | 0x80 for read
    version_reg = ((0x37 << 1) & 0x7E) | 0x80
    result = spi.xfer2([version_reg, 0])
    version = result[1]
    print(f"   RC522 Version register: 0x{version:02X}")

    if version == 0x91 or version == 0x92:
        print("   ✓ RC522 chip detected (v1.0 or v2.0)")
    elif version == 0x88:
        print("   ✓ Fudan FM17522 clone detected")
    elif version == 0x00 or version == 0xFF:
        print("   ✗ No response from RC522 - check wiring!")
        print("     - Is MOSI connected to RC522 MOSI?")
        print("     - Is MISO connected to RC522 MISO?")
        print("     - Is SCK connected to RC522 SCK?")
        print("     - Is SDA connected to CE0 (GPIO 8)?")
    else:
        print(f"   ? Unknown chip version: 0x{version:02X}")

    spi.close()
except Exception as e:
    print(f"   ✗ SPI Error: {e}")
    print("   Is SPI enabled? Run: sudo raspi-config -> Interface Options -> SPI")

# Test reset pin
print("\n2. Testing RST pin...")
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
try:
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    print(f"   ✓ RST pin (GPIO {RST_PIN}) toggles OK")
except Exception as e:
    print(f"   ✗ RST pin error: {e}")
    
# Test with pi-rc522
print("\n3. Testing pi-rc522 library...")
try:
    from pirc522 import RFID
    rdr = RFID(pin_rst=RST_PIN, pin_ce=0, pin_irq=None, pin_mode=GPIO.BCM)

    # Manual antenna on
    rdr.init()

    print("   Library initialized")

    print("\n4. Scanning for tags (10 seconds)...")
    print("   Hold tag directly on the reader...")

    start = time.time()
    found = False

    while time.time() - start < 10:
        rdr.init()
        (error, tag_type) = rdr.request()

        if not error:
            print(f"\n   ✓ Tag detected! Type: {tag_type}")
            (error, uid) = rdr.anticoll()
            if not error:
                uid_hex = ''.join(format(x, '02X') for x in uid)
                print(f"   ✓ UID: {uid_hex}")
                found = True
                break
            else:
                print("   ✗ Anti-collision failed")

        # Show we're alive
        elapsed = int(time.time() - start)
        print(f"\r   Scanning... {10-elapsed}s remaining  ", end='', flush=True)
        time.sleep(0.1)

    if not found:
        print("\n   ✗ No tag detected in 10 seconds")

    rdr.cleanup()

except Exception as e:
    print(f"   ✗ Error: {e}")

GPIO.cleanup()