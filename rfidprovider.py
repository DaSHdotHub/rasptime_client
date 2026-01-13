from kivy.logger import Logger
import RPi.GPIO as GPIO


class RfidProvider:

    def __init__(self, bus, device, irq, rst):
        """
        Initializes RFID device if needed library is installed.
        Running in developer mode if not.
        :param bus: SPI device's bus number
        :param device: SPI device's device number
        :param irq: GPIO connected to interrupt pin (can be None)
        :param rst: GPIO connected to reset pin
        """
        self.dev_mode = False
        self.reader = None
        
        try:
            # Disable GPIO warnings before importing MFRC522
            GPIO.setwarnings(False)
            
            from mfrc522 import MFRC522
            # Use base MFRC522 class to specify custom SPI bus
            self.reader = MFRC522(bus=bus, device=device, pin_rst=rst)
            Logger.info(f'RfidProvider: RFID reader initialized on /dev/spidev{bus}.{device}')
        except ImportError:
            Logger.warning('RfidProvider: mfrc522 library not found. Running in developer mode')
            self.dev_mode = True
        except FileNotFoundError:
            Logger.warning('RfidProvider: SPI device not found. Running in developer mode (RFID not connected)')
            self.dev_mode = True
        except Exception as e:
            Logger.warning(f'RfidProvider: Failed to initialize RFID reader: {str(e)}')
            Logger.warning('RfidProvider: Running in developer mode')
            self.dev_mode = True

    def read_uid(self):
        """
        Read tag UID
        :return: String id or None if no tag detected
        """
        if self.dev_mode:
            return None
        
        try:
            # Wait for tag using proper MFRC522 methods
            (status, tag_type) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
            if status != self.reader.MI_OK:
                return None
                
            # Get UID
            (status, uid) = self.reader.MFRC522_Anticoll()
            if status != self.reader.MI_OK:
                return None
            
            # Convert UID list to string
            uid_str = ''.join(str(x) for x in uid)
            Logger.info(f'RfidProvider: Tag detected - UID: {uid_str}')
            
            # Stop crypto to allow reading again
            self.reader.MFRC522_StopCrypto1()
            
            return uid_str
            
        except KeyboardInterrupt:
            Logger.info('RfidProvider: Read interrupted by user')
            return None
        except Exception as e:
            Logger.error(f'RfidProvider: Error reading tag: {str(e)}')
            return None

    def cleanup(self):
        """
        Free the GPIOs
        :return: None
        """
        if self.dev_mode:
            return
        
        try:
            GPIO.cleanup()
            Logger.info('RfidProvider: GPIO cleanup completed')
        except Exception as e:
            Logger.error(f'RfidProvider: Error during cleanup: {str(e)}')