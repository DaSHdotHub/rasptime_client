#!/usr/bin/env python3
"""Clean RC522 test - matches working script"""
from pirc522 import RFID
import time

print("=== Clean RFID Test ===")
print("Initializing reader (no pin_mode, no pre-set GPIO)...")

# Exactly like your working script
rdr = RFID(pin_rst=24, pin_ce=0, pin_irq=None)

print("Reader initialized. Scanning for 15 seconds...")
print("Hold tag on reader now!\n")

start = time.time()
found = False

while time.time() - start < 15:
    (error, tag_type) = rdr.request()
    if not error:
        (error, uid) = rdr.anticoll()
        if not error:
            uid_str = ":".join(f"{x:02x}" for x in uid)
            print(f"✓ TAG DETECTED! UID: {uid_str}")
            found = True
            time.sleep(1)  # Debounce
    
    elapsed = int(time.time() - start)
    print(f"\rScanning... {15-elapsed}s remaining  ", end='', flush=True)
    time.sleep(0.1)

print("\n")
if not found:
    print("✗ No tag detected")

rdr.cleanup()