from kivy.logger import Logger


class RfidProvider:

    def __init__(self, pin_rst, pin_ce, pin_irq=None):
        """
        Initializes RFID device if needed library is installed.
        Running in developer mode if not.
        :param pin_rst: GPIO connected to reset pin
        :param pin_ce: SPI chip enable pin (0 or 1)
        :param pin_irq: GPIO connected to interrupt pin (can be None)
        """
        self.dev_mode = False
        self.reader = None
        
        try:
            from pirc522 import RFID
            self.reader = RFID(pin_rst=pin_rst, pin_ce=pin_ce, pin_irq=pin_irq)
            Logger.info(f'RfidProvider: RFID reader initialized (RST={pin_rst}, CE={pin_ce}, IRQ={pin_irq})')
        except ImportError as e:
            Logger.warning(f'RfidProvider: pi-rc522 library not found: {e}. Running in developer mode')
            self.dev_mode = True
        except FileNotFoundError as e:
            Logger.warning(f'RfidProvider: SPI device not found: {e}. Running in developer mode')
            self.dev_mode = True
        except Exception as e:
            Logger.warning(f'RfidProvider: Failed to initialize RFID reader: {str(e)}')
            Logger.warning('RfidProvider: Running in developer mode')
            self.dev_mode = True

    def read_uid(self):
        """
        Read tag UID (non-blocking poll)
        :return: String id or None if no tag detected
        """
        if self.dev_mode:
            return None
        
        try:
            # Reset the reader state and init for fresh read
            self.reader.init()
            
            # Request tag
            (error, tag_type) = self.reader.request()
            if error:
                return None
            
            Logger.debug(f'RfidProvider: Tag type detected: {tag_type}')
                
            # Get UID via anti-collision
            (error, uid) = self.reader.anticoll()
            if error:
                Logger.debug('RfidProvider: Anti-collision failed')
                return None
            
            # Convert UID list to string (use hex format for standard UID representation)
            uid_str = ''.join(format(x, '02X') for x in uid)
            Logger.info(f'RfidProvider: Tag detected - UID: {uid_str}')
            
            # Stop crypto to allow reading again
            self.reader.stop_crypto()
            
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
            self.reader.cleanup()
            Logger.info('RfidProvider: GPIO cleanup completed')
        except Exception as e:
            Logger.error(f'RfidProvider: Error during cleanup: {str(e)}')