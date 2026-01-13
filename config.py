"""
Timeclock server address
"""
hostname = 'localhost'
port = '8000'

"""
Authorization of the timeclock's server special terminal user
"""
terminal_id = '4'
api_key = 'tRu4Y316ypP6Kfce4L4c'

"""
Locale has to be installed on the system
Languages currently supported: de, en
"""
locale = 'de_DE.utf8'
lang = 'de'

"""
RFID Reader (RC522) Configuration
SPI Bus and Device: /dev/spidev{bus}.{device}
Using SPI0 CE0 for RFID reader
"""
bus = 0          # SPI bus (spidev0.x)
device = 0       # Chip select (CE0)
irq = None       # Not connected
rst = 24         # GPIO 24 (Pin 18) - Reset pin

"""
Buzzer Configuration (TMB12A03)
"""
buzzer_pin = 17  # GPIO 17 (Pin 11)
buzzer_enabled = True  # Set to False to disable buzzer
