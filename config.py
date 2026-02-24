"""
Timeclock server address
"""
hostname = '192.168.178.157'
port = '8081'

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
pin_rst = 24
pin_ce = 0
pin_irq = None
"""
Buzzer Configuration (TMB12A03)
"""
buzzer_pin = 17  # GPIO 17 (Pin 11)
buzzer_enabled = True  # Set to False to disable buzzer

"""
Demo Mode - Set to True to run without backend server
Uses mock data provider that simulates API calls
"""
demo_mode = False  # Set to False for production

"""
Admin RFID tag (optional - for direct admin screen access)
"""
admin_rfid = '0B79D206A6'  # Set to your admin tag or None to disable