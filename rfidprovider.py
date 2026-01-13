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
            from mfrc522 import SimpleMFRC522
            # SimpleMFRC522 uses default pins, but we can initialize the base MFRC522 if needed
            self.reader = SimpleMFRC522()
            Logger.info('RfidProvider: RFID reader initialized successfully')
        except ImportError:
            Logger.warning('RfidProvider: mfrc522 library not found. Running in developer mode')
            self.dev_mode = True
        except Exception as e:
            Logger.error(f'RfidProvider: Failed to initialize RFID reader: {str(e)}')
            self.dev_mode = True

    def read_uid(self):
        """
        Read tag UID
        :return: String id or None if no tag detected
        """
        if self.dev_mode:
            Logger.debug('RfidProvider: Developer mode - simulating tag read')
            return None
        
        try:
            Logger.debug('RfidProvider: Waiting for RFID tag...')
            # SimpleMFRC522.read() returns (id, text)
            # Use read_id() for just the ID, or read() for both
            uid, text = self.reader.read()
            uid_str = str(uid)
            Logger.info(f'RfidProvider: Tag detected - UID: {uid_str}')
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