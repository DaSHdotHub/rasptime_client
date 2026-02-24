import RPi.GPIO as GPIO
import time
from kivy.logger import Logger
from threading import Thread


class Buzzer:
    """
    Control active buzzer for acoustic feedback
    """

    def __init__(self, pin):
        """
        Initialize buzzer on specified GPIO pin
        :param pin: GPIO pin number (BCM mode)
        """
        self.pin = pin
        self.enabled = True
        
        try:
            GPIO.setwarnings(False)
            
            # Don't set GPIO mode - use whatever mode is already set by pirc522
            current_mode = GPIO.getmode()
            Logger.debug(f'Buzzer: Current GPIO mode: {current_mode}')
            
            if current_mode is None:
                Logger.error('Buzzer: No GPIO mode set. RFID reader should be initialized first.')
                self.enabled = False
                return
            
            # If pirc522 is using BOARD mode, we need to convert BCM pin to BOARD pin
            if current_mode == GPIO.BOARD:
                bcm_to_board = {
                    17: 11,
                    27: 13,
                    22: 15,
                }
                if pin in bcm_to_board:
                    self.pin = bcm_to_board[pin]
                    Logger.info(f'Buzzer: Converted BCM {pin} to BOARD {self.pin}')
                else:
                    Logger.error(f'Buzzer: Unknown BCM pin {pin} for BOARD mode conversion')
                    self.enabled = False
                    return
            
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)
            Logger.info(f'Buzzer: Initialized on pin {self.pin}')
        except Exception as e:
            Logger.error(f'Buzzer: Failed to initialize: {e}')
            self.enabled = False

    def beep(self, duration=0.1):
        """
        Single beep
        :param duration: beep duration in seconds
        """
        if not self.enabled:
            return
            
        try:
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(self.pin, GPIO.LOW)
        except Exception as e:
            Logger.error(f'Buzzer: Error during beep: {e}')

    def beep_async(self, duration=0.1):
        """
        Non-blocking beep in separate thread
        :param duration: beep duration in seconds
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self.beep, args=(duration,), daemon=True)
        thread.start()

    def clock_in(self):
        """
        Clock in: single 1.5s beep
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._clock_in_pattern, daemon=True)
        thread.start()

    def _clock_in_pattern(self):
        """
        Internal method for clock in pattern
        Single 1.5 second beep
        """
        try:
            self.beep(1.5)
        except Exception as e:
            Logger.error(f'Buzzer: Error in clock in pattern: {e}')

    def clock_out(self):
        """
        Clock out: two 0.75s beeps with 0.25s pause
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._clock_out_pattern, daemon=True)
        thread.start()

    def _clock_out_pattern(self):
        """
        Internal method for clock out pattern
        Two 0.75s beeps with 0.25s pause between
        """
        try:
            self.beep(0.75)
            time.sleep(0.25)
            self.beep(0.75)
        except Exception as e:
            Logger.error(f'Buzzer: Error in clock out pattern: {e}')

    def error(self):
        """
        Error/Unknown RFID: three short beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._error_pattern, daemon=True)
        thread.start()

    def _error_pattern(self):
        """
        Internal method for error pattern
        Three short beeps (0.15s each, 0.1s pause)
        """
        try:
            for _ in range(3):
                self.beep(0.15)
                time.sleep(0.1)
        except Exception as e:
            Logger.error(f'Buzzer: Error in error pattern: {e}')

    def warning(self):
        """
        Warning pattern: two short beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._warning_pattern, daemon=True)
        thread.start()

    def _warning_pattern(self):
        """
        Internal method for warning beep pattern
        """
        try:
            self.beep(0.2)
            time.sleep(0.15)
            self.beep(0.2)
        except Exception as e:
            Logger.error(f'Buzzer: Error in warning pattern: {e}')

    def admin_mode(self):
        """
        Admin mode activated: ascending beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._admin_pattern, daemon=True)
        thread.start()

    def _admin_pattern(self):
        """
        Internal method for admin mode pattern
        Ascending beeps to indicate special mode
        """
        try:
            self.beep(0.1)
            time.sleep(0.1)
            self.beep(0.2)
            time.sleep(0.1)
            self.beep(0.3)
        except Exception as e:
            Logger.error(f'Buzzer: Error in admin pattern: {e}')

    def registration_success(self):
        """
        Registration success: happy confirmation beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._registration_success_pattern, daemon=True)
        thread.start()

    def _registration_success_pattern(self):
        """
        Internal method for registration success pattern
        """
        try:
            self.beep(0.1)
            time.sleep(0.05)
            self.beep(0.1)
            time.sleep(0.05)
            self.beep(0.3)
        except Exception as e:
            Logger.error(f'Buzzer: Error in registration success pattern: {e}')

    def success(self):
        """
        Generic success pattern: two short beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._success_pattern, daemon=True)
        thread.start()

    def _success_pattern(self):
        """
        Internal method for success beep pattern
        """
        try:
            self.beep(0.1)
            time.sleep(0.1)
            self.beep(0.1)
        except Exception as e:
            Logger.error(f'Buzzer: Error in success pattern: {e}')

    def cleanup(self):
        """
        Clean up GPIO - only clean up our pin, not all GPIO
        """
        if not self.enabled:
            return
            
        try:
            GPIO.output(self.pin, GPIO.LOW)
            Logger.info('Buzzer: Cleanup completed')
        except Exception as e:
            Logger.error(f'Buzzer: Error during cleanup: {e}')