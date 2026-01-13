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
            GPIO.setwarnings(False)  # Disable warnings
            
            # Only set mode if not already set
            try:
                GPIO.setmode(GPIO.BCM)
            except ValueError:
                # Mode already set, that's fine
                pass
                
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)
            Logger.info(f'Buzzer: Initialized on GPIO {self.pin}')
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
        Clean up GPIO
        """
        if not self.enabled:
            return
            
        try:
            GPIO.output(self.pin, GPIO.LOW)
            Logger.info('Buzzer: Cleanup completed')
        except Exception as e:
            Logger.error(f'Buzzer: Error during cleanup: {e}')


# Test function
if __name__ == '__main__':
    """
    Test buzzer patterns
    """
    print("Testing buzzer on GPIO 17")
    buzzer = Buzzer(17)
    
    try:
        print("Single beep...")
        buzzer.beep()
        time.sleep(1)
        
        print("Success pattern...")
        buzzer.success()
        time.sleep(1)
        
        print("Error pattern...")
        buzzer.error()
        time.sleep(1)
        
        print("Warning pattern...")
        buzzer.warning()
        time.sleep(1)
        
        print("Clock in pattern...")
        buzzer.clock_in()
        time.sleep(1)
        
        print("Clock out pattern...")
        buzzer.clock_out()
        time.sleep(1)
        
        print("Test complete!")
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        buzzer.cleanup()
        GPIO.cleanup()