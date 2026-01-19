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
                # BCM to BOARD mapping for common pins
                bcm_to_board = {
                    17: 11,  # GPIO17 = Pin 11
                    27: 13,  # GPIO27 = Pin 13
                    22: 15,  # GPIO22 = Pin 15
                    # Add more mappings if needed
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

    def success(self):
        """
        Success pattern: two short beeps
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

    def error(self):
        """
        Error pattern: one long beep
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self.beep, args=(0.5,), daemon=True)
        thread.start()

    def warning(self):
        """
        Warning pattern: three short beeps
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
            for _ in range(3):
                self.beep(0.08)
                time.sleep(0.08)
        except Exception as e:
            Logger.error(f'Buzzer: Error in warning pattern: {e}')

    def clock_in(self):
        """
        Clock in pattern: ascending beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._clock_in_pattern, daemon=True)
        thread.start()

    def _clock_in_pattern(self):
        """
        Internal method for clock in pattern
        """
        try:
            self.beep(0.1)
            time.sleep(0.05)
            self.beep(0.15)
        except Exception as e:
            Logger.error(f'Buzzer: Error in clock in pattern: {e}')

    def clock_out(self):
        """
        Clock out pattern: descending beeps
        """
        if not self.enabled:
            return
            
        thread = Thread(target=self._clock_out_pattern, daemon=True)
        thread.start()

    def _clock_out_pattern(self):
        """
        Internal method for clock out pattern
        """
        try:
            self.beep(0.15)
            time.sleep(0.05)
            self.beep(0.1)
        except Exception as e:
            Logger.error(f'Buzzer: Error in clock out pattern: {e}')

    def cleanup(self):
        """
        Clean up GPIO - only clean up our pin, not all GPIO
        """
        if not self.enabled:
            return
            
        try:
            GPIO.output(self.pin, GPIO.LOW)
            # Don't call GPIO.cleanup() - let the RFID reader handle that
            Logger.info('Buzzer: Cleanup completed')
        except Exception as e:
            Logger.error(f'Buzzer: Error during cleanup: {e}')