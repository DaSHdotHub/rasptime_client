from kivy.logger import Logger


class RfidProvider:

    def __init__(self, pin_rst=24, pin_ce=0, pin_irq=None):
        """
        Initializes RFID device if needed library is installed.
        Running in developer mode if not.
        :param pin_rst: GPIO connected to reset pin (default: 24)
        :param pin_ce: SPI CE pin (default: 0)
        :param pin_irq: GPIO connected to interrupt pin (default: None)
        """
        self.dev_mode = False
        self.reader = None
        
        try:
            from pirc522 import RFID
            self.reader = RFID(pin_rst=pin_rst, pin_ce=pin_ce, pin_irq=pin_irq)
            Logger.info(f'RfidProvider: RFID reader initialized (RST={pin_rst}, CE={pin_ce}, IRQ={pin_irq})')
        except ImportError:
            Logger.warning('RfidProvider: pi-rc522 library not found. Running in developer mode')
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
            # Request tag (non-blocking check)
            (error, tag_type) = self.reader.request()
            if error:
                return None
                
            # Get UID via anti-collision
            (error, uid) = self.reader.anticoll()
            if error:
                return None
            
            # Convert UID list to string
            uid_str = ''.join(str(x) for x in uid)
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

    def read_uid_blocking(self):
        """
        Read tag UID (blocking - waits for tag)
        :return: String id or None if error/interrupted
        """
        if self.dev_mode:
            return None
        
        try:
            # Wait for tag (blocking)
            self.reader.wait_for_tag()
            
            # Request tag
            (error, tag_type) = self.reader.request()
            if error:
                return None
                
            # Get UID via anti-collision
            (error, uid) = self.reader.anticoll()
            if error:
                return None
            
            # Convert UID list to string
            uid_str = ''.join(str(x) for x in uid)
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