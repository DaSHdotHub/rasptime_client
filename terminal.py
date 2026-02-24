import time
import locale
import subprocess
from threading import Thread
from gettext import translation

from kivy.app import App
from kivy import require
from kivy.clock import Clock
from kivy.config import Config
from kivy.logger import Logger
from kivy.properties import ObjectProperty, StringProperty

from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen

import config
if config.demo_mode:
    from dataprovider_mock import DataProvider
    Logger.info('Terminal: Running in DEMO MODE')
else:
    from dataprovider import DataProvider
from rfidprovider import RfidProvider
from beep import Buzzer

require('2.0.0')


def _(*args):
    """
    Translator
    :param args: text to translate
    :return: translated text
    """
    return App.get_running_app().get_text(*args)


def change_screen(name, data=None):
    """
    Show another screen of the app
    :param name: name of the screen (terminal.kv)
    :param data: data to show on the selected screen
    :return: None
    """
    app = App.get_running_app()
    if app and app.root:
        app.root.current = name
        if data is not None:
            app.root.get_screen(name).show(data)


def show_user(tag):
    """
    Shows user info screen
    :param tag: serial number
    :return: None
    """
    change_screen('user', tag)


def show_error(message):
    """
    Shows error screen
    :param message: text to show
    :return: None
    """
    change_screen('error', message)


class CurrentWorkingWidget(StackLayout):
    """
    Shows the currently working employees in a table
    """

    def __init__(self, **kwargs):
        """
        Starts update thread every 15 seconds
        :param kwargs: kivy
        """
        super(CurrentWorkingWidget, self).__init__(**kwargs)
        self.widget_list = []
        self.worker = None
        Clock.schedule_interval(self.start_thread, 15)
        self.start_thread()

    def start_thread(self, *args):
        """
        Checks if update thread is running and starts it if not
        :param args: kivy
        :return: None
        """
        if self.worker and self.worker.is_alive():
            Logger.warning('Terminal: Update thread for working users is still running')
        else:
            self.worker = Thread(target=self.update_widgets, daemon=True)
            self.worker.start()

    def update_widgets(self, *args):
        """
        Update Label widgets without removing them (no flickering on RPI Zero W)
        by diffing current and new widgets. Adding and removing in main thread via
        kivy's schedule_once()
        :param args: kivy things
        :return: None
        """
        try:
            app = App.get_running_app()
            if not app or not hasattr(app, 'data_provider'):
                Logger.warning('Terminal: Data provider not yet available')
                return
                
            working = app.data_provider.working_users()
            new_widget_data = []
            
            if working and len(working) > 0:
                for name, clock_in, user_id in working:
                    if name is None:
                        name = _('Unknown ') + str(user_id)
                    display_text = f'{clock_in} {name}' if clock_in else name
                    new_widget_data.append((display_text,))

            Clock.schedule_once(lambda x: self.update_widgets_main_thread(new_widget_data), 0)
        except Exception as e:
            Logger.error(f'Terminal: Error updating working employees: {e}')

    def update_widgets_main_thread(self, new_widget_data):
        """
        Create and update widgets in main thread
        :param new_widget_data: list of tuples containing widget text
        """
        try:
            new_widgets = []
            for text_data in new_widget_data:
                item = Label(
                    text_size=(250, 40),
                    halign='left',
                    font_size='20sp',
                    size_hint=(0.3, 0.01),
                    text=text_data[0]
                )
                new_widgets.append(item)

            remove = [old for old in self.widget_list 
                     if not any(old.text == new.text for new in new_widgets)]

            add = [new for new in new_widgets 
                  if not any(old.text == new.text for old in self.widget_list)]

            self.remove_working_employees(remove)
            self.add_working_employees(add)
        except Exception as e:
            Logger.error(f'Terminal: Error in main thread widget update: {e}')

    def add_working_employees(self, items):
        """
        Adds labels to table and to internal list
        :param items: labels
        :return: None
        """
        for item in items:
            self.add_widget(item)
            self.widget_list.append(item)

    def remove_working_employees(self, items):
        """
        Removes labels from table and from internal list
        :param items: labels
        :return: None
        """
        for item in items:
            self.remove_widget(item)
            self.widget_list.remove(item)


class ClockWidget(ButtonBehavior, BoxLayout):
    """
    Home screen clock
    """
    hours_minutes = StringProperty()
    seconds = StringProperty()
    date_string = StringProperty()

    def __init__(self, **kwargs):
        """
        Schedules clock update for every second
        :param kwargs: kivy
        """
        super(ClockWidget, self).__init__(**kwargs)
        Clock.schedule_interval(self.update_time, 1)
        self.update_time()
        self.press_time = time.time()
        self.press_counter = 0

    def update_time(self, *args):
        """
        Updates current time
        :param args: kivy
        :return: None
        """
        self.hours_minutes = time.strftime('%H:%M', time.localtime())
        self.seconds = time.strftime('%S', time.localtime())
        self.date_string = time.strftime('%A, %d. %b %Y', time.localtime())

    def on_press(self):
        """
        Hidden admin screen, press 3 times in 5 seconds to get there
        :return: None
        """
        current_time = time.time()
        if current_time - self.press_time < 5:
            self.press_counter += 1
            if self.press_counter == 3:
                self.press_counter = 0
                change_screen('admin', None)
        else:
            self.press_counter = 1
            self.press_time = current_time


class BackButton(ButtonBehavior, Image):
    pass


class HomeScreen(Screen):
    """
    Home screen with clock and currently working employees
    """
    current_working = ObjectProperty()

    def __init__(self, **kwargs):
        super(HomeScreen, self).__init__(**kwargs)
        self.worker = None
        self.running = False

    def on_enter(self, *args):
        """
        Starts thread that waits for a RFID tag
        :param args: kivy
        :return: None
        """
        self.running = True
        if self.worker and self.worker.is_alive():
            Logger.warning('Terminal: RFID worker thread not exited correctly')
        else:
            self.worker = Thread(target=self.read_rfid_loop, daemon=True)
            self.worker.start()

    def on_leave(self, *args):
        """
        Stop RFID reading when leaving screen
        """
        self.running = False

    def read_rfid_loop(self):
        """
        Continuously read RFID tags while on home screen
        Handles normal clock in/out and registration mode
        :return: None
        """
        Logger.info('Terminal: RFID reading loop started')
        
        while self.running:
            try:
                uid = rp.read_uid()
                
                if not uid or self.manager.current != 'home':
                    time.sleep(0.1)
                    continue

                Logger.info(f'Terminal: RFID tag scanned: {uid}')

                # Check if registration mode is active (frontend waiting for RFID)
                session_id = dp.check_registration_mode()
                if session_id:
                    Logger.info(f'Terminal: Registration mode active, submitting tag')
                    success = dp.submit_registration(session_id, uid)
                    if success:
                        if buzzer:
                            buzzer.registration_success()
                        Logger.info(f'Terminal: RFID {uid} submitted for registration')
                    else:
                        if buzzer:
                            buzzer.error()
                        Logger.error(f'Terminal: Failed to submit RFID for registration')
                    time.sleep(2)
                    continue

                # Check if this is the admin tag
                if hasattr(config, 'admin_rfid') and uid == config.admin_rfid:
                    Logger.info('Terminal: Admin tag detected')
                    if buzzer:
                        buzzer.admin_mode()
                    Clock.schedule_once(lambda x: change_screen('admin', None), 0)
                    time.sleep(1)
                    continue

                # Normal mode - check user and punch
                user_info = dp.user_info(uid)
                
                if user_info:
                    name, image, user_id, clocked_in = user_info
                    Logger.info(f'Terminal: User {name} (ID: {user_id}) - currently {"clocked in" if clocked_in else "clocked out"}')
                    
                    # Punch (toggles clock in/out)
                    result = dp.punch(uid)
                    
                    if result:
                        action, message, display_name = result
                        Logger.info(f'Terminal: Punch result - {action}: {message}')
                        
                        if action == 'CLOCK_IN':
                            # Clock in: single 1.5s beep
                            if buzzer:
                                buzzer.clock_in()
                            Clock.schedule_once(
                                lambda x, n=display_name: self.show_clock_screen(True, n), 0
                            )
                        elif action == 'CLOCK_OUT':
                            # Clock out: two 0.75s beeps with 0.25s pause
                            if buzzer:
                                buzzer.clock_out()
                            Clock.schedule_once(
                                lambda x, n=display_name: self.show_clock_screen(False, n), 0
                            )
                        else:
                            Logger.warning(f'Terminal: Unknown action: {action}')
                            if buzzer:
                                buzzer.warning()
                    else:
                        # Punch failed (server error)
                        Logger.error('Terminal: Punch request failed')
                        if buzzer:
                            buzzer.error()
                        Clock.schedule_once(
                            lambda x: show_error(_('Server error. Please try again.')), 0
                        )
                else:
                    # Unknown RFID tag: three short beeps
                    Logger.warning(f'Terminal: Unknown RFID tag: {uid}')
                    if buzzer:
                        buzzer.error()
                    Clock.schedule_once(
                        lambda x, t=uid: show_error(_('Unknown tag: ') + str(t)), 0
                    )
                
                # Cooldown to prevent double scans
                time.sleep(1.5)
                
            except Exception as e:
                Logger.error(f'Terminal: Error in RFID loop: {e}')
                time.sleep(1)
        
        Logger.info('Terminal: RFID reading loop stopped')

    def show_clock_screen(self, clock_in, name):
        """
        Show welcome/goodbye screen
        :param clock_in: True if clocking in, False if clocking out
        :param name: User's display name
        """
        change_screen('clock')
        screen = self.manager.get_screen('clock')
        screen.show(clock_in, name)


class UserScreen(Screen):
    """
    User screen with image, info about worked hours and arrive/leave buttons
    Note: This screen is now optional - direct punch from HomeScreen is preferred
    """
    welcome = StringProperty()
    today_hours = StringProperty()
    week_hours = StringProperty()
    last_week_hours = StringProperty()
    holidays = StringProperty()
    user_image = StringProperty()

    def __init__(self, **kwargs):
        super(UserScreen, self).__init__(**kwargs)
        self.user_id = None
        self.rfid_tag = None
        self.worker = None

    def show(self, tag):
        """
        Updates properties with current user data and
        starts thread to load info about worked hours later
        :param tag: serial number
        :return: None
        """
        self.rfid_tag = tag
        self.today_hours = ''
        self.week_hours = ''
        self.last_week_hours = ''
        self.holidays = ''

        try:
            resp = dp.user_info(tag)
            if not resp:
                show_error(_('User does not exist: ') + str(tag))
                return

            name, image, user_id, clocked_in = resp
            self.welcome = _('Hello ') + name.split(' ')[0] + '!'
            self.user_image = image
            self.user_id = user_id

            if self.worker and self.worker.is_alive():
                Logger.error('Terminal: Get user data thread is still running')
            else:
                self.worker = Thread(target=self.get_data, daemon=True)
                self.worker.start()
        except Exception as e:
            Logger.error(f'Terminal: Error showing user: {e}')
            show_error(_('Error loading user data'))

    def get_data(self):
        """
        Retrieves info about worked hours, update of UI in main thread
        :return: None
        """
        try:
            if self.user_id:
                resp = dp.user_work_summary(self.user_id)
                if resp:
                    Clock.schedule_once(lambda x: self.update_user_data(resp), 0)
        except Exception as e:
            Logger.error(f'Terminal: Error getting user data: {e}')

    def update_user_data(self, data):
        """
        Updates UI with given data
        :param data: tuple with (today_minutes, week_minutes, last_week_minutes, vacation_days)
        :return: None
        """
        try:
            today, week, last_week, vacation = data
            self.today_hours = f"{int(today / 60):02d}:{today % 60:02d} h"
            self.week_hours = f"{int(week / 60):02d}:{week % 60:02d} h"
            self.last_week_hours = f"{int(last_week / 60):02d}:{last_week % 60:02d} h"
            self.holidays = str(vacation) + _(' Days')
        except Exception as e:
            Logger.error(f'Terminal: Error updating user data: {e}')

    def clock_in(self):
        """
        Clocks in user using punch endpoint
        :return: None
        """
        if not self.rfid_tag:
            Logger.error('Terminal: No RFID tag set to clock in')
            return

        try:
            result = dp.punch(self.rfid_tag)
            if result:
                action, message, name = result
                if action == 'CLOCK_IN':
                    if buzzer:
                        buzzer.clock_in()
                    change_screen('clock')
                    screen = self.parent.get_screen('clock')
                    screen.show(True, name)
                else:
                    # Already clocked in, this shouldn't happen
                    if buzzer:
                        buzzer.warning()
                    show_error(_('You are already clocked in.'))
            else:
                if buzzer:
                    buzzer.error()
                show_error(_('Server error. Could not clock in.'))
        except Exception as e:
            Logger.error(f'Terminal: Error clocking in: {e}')
            if buzzer:
                buzzer.error()
            show_error(_('Error clocking in'))

    def clock_out(self):
        """
        Clocks out user using punch endpoint
        :return: None
        """
        if not self.rfid_tag:
            Logger.error('Terminal: No RFID tag set to clock out')
            return

        try:
            result = dp.punch(self.rfid_tag)
            if result:
                action, message, name = result
                if action == 'CLOCK_OUT':
                    if buzzer:
                        buzzer.clock_out()
                    change_screen('clock')
                    screen = self.parent.get_screen('clock')
                    screen.show(False, name)
                else:
                    # Already clocked out, this shouldn't happen
                    if buzzer:
                        buzzer.warning()
                    show_error(_('You are already clocked out.'))
            else:
                if buzzer:
                    buzzer.error()
                show_error(_('Server error. Could not clock out.'))
        except Exception as e:
            Logger.error(f'Terminal: Error clocking out: {e}')
            if buzzer:
                buzzer.error()
            show_error(_('Error clocking out'))


class ClockInOutScreen(Screen):
    """
    Welcome and goodbye screen
    """
    current_time = StringProperty()
    message = StringProperty()
    image = StringProperty()
    user_name = StringProperty()

    def __init__(self, **kwargs):
        super(ClockInOutScreen, self).__init__(**kwargs)
        self.timer = None

    def back(self):
        """
        Back button, cancels automatic back
        :return: None
        """
        if self.timer:
            self.timer.cancel()
        change_screen('home')

    def show(self, clock_in, name=None):
        """
        Shows Welcome/Goodbye message with door image and
        starts timer to go back after 3 seconds
        :param clock_in: True if user clocked in
        :param name: User's display name (optional)
        :return: None
        """
        self.current_time = time.strftime('%H:%M Uhr', time.localtime())
        self.user_name = name if name else ''
        
        if clock_in:
            self.image = 'images/clockin.png'
            if name:
                self.message = _('Welcome, ') + name.split(' ')[0] + '!'
            else:
                self.message = _('Welcome!')
        else:
            self.image = 'images/clockout.png'
            if name:
                self.message = _('Goodbye, ') + name.split(' ')[0] + '!'
            else:
                self.message = _('Goodbye!')
        
        # Update working employees list
        home_screen = App.get_running_app().root.get_screen('home')
        if home_screen and home_screen.current_working:
            home_screen.current_working.start_thread()
        
        # Auto-return to home after 3 seconds
        if self.timer:
            self.timer.cancel()
        self.timer = Clock.schedule_once(lambda x: change_screen('home'), 3)


class ErrorScreen(Screen):
    message = StringProperty()

    def show(self, message):
        """
        Shows error message
        :param message: error message
        :return: None
        """
        self.message = message

    @staticmethod
    def back():
        """
        Back button
        :return: None
        """
        change_screen('home')


class AdminScreen(Screen):
    message = StringProperty()

    def on_enter(self, *args):
        """
        Shows time and all IP addresses
        :param args: kivy
        :return: None
        """
        try:
            t = time.strftime("%a, %d %b %Y %H:%M:%S")
            result = subprocess.run(['hostname', '-I'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            ips = result.stdout.strip().split(' ')
            i = '\n'.join(ips)
            
            # Add backend health status
            health = "Backend: "
            if dp.health_check():
                health += "✓ Online"
            else:
                health += "✗ Offline"
            
            self.message = f'{t}\n{i}\n\n{health}'
        except Exception as e:
            Logger.error(f'Terminal: Error getting admin info: {e}')
            self.message = time.strftime("%a, %d %b %Y %H:%M:%S") + '\nError getting IPs'

    @staticmethod
    def back():
        """
        Back button
        :return: None
        """
        change_screen('home')


class GlobalScreenManager(ScreenManager):
    """
    Manager for different screens
    """

    @staticmethod
    def build():
        return ScreenManager()


class Terminal(App):
    """
    Main app
    """

    def __init__(self, lang, data_provider):
        """
        Initializes kivy app and sets language
        :param lang: supported language e.g. 'de'
        :param data_provider: DataProvider instance
        """
        super().__init__()
        self.lang = translation('terminal', localedir='lang', languages=[lang], fallback=True)
        self.data_provider = data_provider

    def build(self):
        """
        Sets window settings and starts ScreenManager with first screen (home)
        :return: GlobalScreenManager
        """
        Config.set('graphics', 'resizable', False)
        Config.set('graphics', 'borderless', True)
        Config.set('graphics', 'height', 480)
        Config.set('graphics', 'width', 800)
        Config.set('graphics', 'show_cursor', '0')
        
        try:
            locale.setlocale(locale.LC_ALL, config.locale)
        except Exception as e:
            Logger.warning(f'Terminal: Could not set locale {config.locale}: {e}')
            Logger.info('Terminal: Falling back to default locale')

        return GlobalScreenManager()

    def on_stop(self):
        """
        Graceful exit
        :return: None
        """
        Logger.info('Terminal: Application stopping, cleanup starting')
        try:
            if rp:
                rp.cleanup()
        except Exception as e:
            Logger.error(f'Terminal: Error during RFID cleanup: {e}')
        try:
            if buzzer:
                buzzer.cleanup()
        except Exception as e:
            Logger.error(f'Terminal: Error during buzzer cleanup: {e}')

    def get_text(self, *args):
        """
        Translation
        :param args: text
        :return: translated text
        """
        return self.lang.gettext(*args)


# Global instances
dp = None
rp = None
buzzer = None


if __name__ == '__main__':
    try:
        Logger.info('Terminal: Initializing application')
        
        # Initialize data provider
        dp = DataProvider(config.hostname, config.port, config.terminal_id, config.api_key)
        
        # Check backend connectivity
        if dp.health_check():
            Logger.info('Terminal: Backend connection successful')
        else:
            Logger.warning('Terminal: Backend not reachable, continuing anyway')
        
        # Initialize RFID FIRST (pi-rc522 sets GPIO mode)
        rp = RfidProvider(config.pin_rst, config.pin_ce, config.pin_irq)
        
        # Initialize buzzer AFTER RFID (uses existing GPIO mode)
        if config.buzzer_enabled:
            buzzer = Buzzer(config.buzzer_pin)
            buzzer.success()  # Startup beep
        
        # Start application
        Terminal(config.lang, dp).run()
        
    except KeyboardInterrupt:
        Logger.info('Terminal: Keyboard interrupt received')
        if App.get_running_app():
            App.get_running_app().stop()
    except Exception as e:
        Logger.critical(f'Terminal: Fatal error: {e}')
        import traceback
        traceback.print_exc()
        raise
    finally:
        Logger.info('Terminal: Final cleanup')
        if rp:
            try:
                rp.cleanup()
            except Exception as e:
                Logger.error(f'Terminal: Error during final RFID cleanup: {e}')
        if buzzer:
            try:
                buzzer.cleanup()
            except Exception as e:
                Logger.error(f'Terminal: Error during final buzzer cleanup: {e}')