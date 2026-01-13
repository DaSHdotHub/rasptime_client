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
        if data:
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
            new_widgets = []
            working = dp.working_users()
            if working and len(working) > 0:
                for name, clock_in, user_id in working:
                    if name is None:
                        name = _('Unknown ') + str(user_id)
                    item = Label(
                        text_size=(250, 40),
                        halign='left',
                        font_size='20sp',
                        size_hint=(0.3, 0.01),
                        text=f'{clock_in} {name}'
                    )
                    new_widgets.append(item)

            # Find widgets to remove
            remove = [old for old in self.widget_list 
                     if not any(old.text == new.text for new in new_widgets)]

            # Find widgets to add
            add = [new for new in new_widgets 
                  if not any(old.text == new.text for old in self.widget_list)]

            Clock.schedule_once(lambda x: self.remove_working_employees(remove), 0)
            Clock.schedule_once(lambda x: self.add_working_employees(add), 0)
        except Exception as e:
            Logger.error(f'Terminal: Error updating working employees: {e}')

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
        :return: None
        """
        while self.running:
            try:
                uid = rp.read_uid()
                if uid and self.manager.current == 'home':
                    if buzzer:
                        buzzer.beep_async(0.1)  # Short beep on tag read
                    Clock.schedule_once(lambda x: show_user(uid), 0)
                    time.sleep(1)
                else:
                    time.sleep(0.1)
            except Exception as e:
                Logger.error(f'Terminal: Error reading RFID: {e}')
                time.sleep(1)


class UserScreen(Screen):
    """
    User screen with image, info about worked hours and arrive/leave buttons
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
        self.worker = None

    def show(self, tag):
        """
        Updates properties with current user data and
        starts thread to load info about worked hours later
        :param tag: serial number
        :return: None
        """
        # Reset display
        self.today_hours = ''
        self.week_hours = ''
        self.last_week_hours = ''
        self.holidays = ''

        try:
            resp = dp.user_info(tag)
            if not resp:
                show_error(_('User does not exist: ') + str(tag))
                return

            self.welcome = _('Hello ') + resp[0].split(' ')[0] + '!'
            self.user_image = resp[1]
            self.user_id = resp[2]

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
        :param data: array with worked minutes and vacation days
        :return: None
        """
        try:
            self.today_hours = f"{int(data[0] / 60):02d}:{data[0] % 60:02d} h"
            self.week_hours = f"{int(data[1] / 60):02d}:{data[1] % 60:02d} h"
            self.last_week_hours = f"{int(data[2] / 60):02d}:{data[2] % 60:02d} h"
            self.holidays = str(data[3]) + _(' Days')
        except Exception as e:
            Logger.error(f'Terminal: Error updating user data: {e}')

    def clock_in(self):
        """
        Clocks in user and shows error or welcome/goodbye screen
        :return: None
        """
        if not self.user_id:
            Logger.error('Terminal: No user ID set to clock in')
            return

        try:
            ret = dp.clock_in(self.user_id)
            if ret:
                change_screen('clock')
                screen = self.parent.get_screen('clock')
                screen.show(True)
            elif ret is False:
                show_error(_('You are already clocked in.'))
            else:
                show_error(_('Server error. Could not clock in user. ID: ') + str(self.user_id))
        except Exception as e:
            Logger.error(f'Terminal: Error clocking in: {e}')
            show_error(_('Error clocking in'))

def clock_out(self):
    """
    Clocks out user and shows error or welcome/goodbye screen
    :return: None
    """
    if not self.user_id:
        Logger.error('Terminal: No user ID set to clock out')
        return

    try:
        ret = dp.clock_out(self.user_id)
        if ret:
            if buzzer:
                buzzer.clock_out()  # Clock out sound
            change_screen('clock')
            screen = self.parent.get_screen('clock')
            screen.show(False)
        elif ret is False:
            if buzzer:
                buzzer.warning()  # Warning sound
            show_error(_('You are already clocked out.'))
        else:
            if buzzer:
                buzzer.error()  # Error sound
            show_error(_('Server error. Could not clock out user. ID: ') + str(self.user_id))
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

    def show(self, clock_in):
        """
        Shows Welcome/Goodbye message with door image and
        starts timer to go back after 3 seconds
        :param clock_in: True if user clocked in
        :return: None
        """
        self.current_time = time.strftime('%H:%M Uhr', time.localtime())
        if clock_in:
            self.image = 'images/clockin.png'
            self.message = _('Welcome!')
        else:
            self.image = 'images/clockout.png'
            self.message = _('Goodbye!')
        
        # Update working employees list
        home_screen = App.get_running_app().root.get_screen('home')
        if home_screen and home_screen.current_working:
            home_screen.current_working.start_thread()
        
        # Auto-return to home after 3 seconds
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
            # Use subprocess instead of os.popen
            result = subprocess.run(['hostname', '-I'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            ips = result.stdout.strip().split(' ')
            i = '\n'.join(ips)
            self.message = f'{t}\n{i}'
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

    def __init__(self, lang):
        """
        Initializes kivy app and sets language
        :param lang: supported language e.g. 'de'
        """
        super().__init__()
        self.lang = translation('terminal', localedir='lang', languages=[lang], fallback=True)

    def build(self):
        """
        Sets window settings and starts ScreenManager with first screen (home)
        :return: GlobalScreenManager
        """
        # Set configuration
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
        Logger.info('Terminal: GPIO cleanup and exit')
        try:
            rp.cleanup()
        except Exception as e:
            Logger.error(f'Terminal: Error during cleanup: {e}')

    def get_text(self, *args):
        """
        Translation
        :param args: text
        :return: translated text
        """
        return self.lang.gettext(*args)


if __name__ == '__main__':
    dp = None
    rp = None
    buzzer = None
    
    try:
        Logger.info('Terminal: Initializing application')
        dp = DataProvider(config.hostname, config.port, config.terminal_id, config.api_key)
        rp = RfidProvider(config.bus, config.device, config.irq, config.rst)
        
        # Initialize buzzer if enabled
        if config.buzzer_enabled:
            buzzer = Buzzer(config.buzzer_pin)
        
        Terminal(config.lang).run()
    except KeyboardInterrupt:
        Logger.info('Terminal: Keyboard interrupt received')
        if App.get_running_app():
            App.get_running_app().stop()
    except Exception as e:
        Logger.critical(f'Terminal: Fatal error: {e}')
        raise
    finally:
        if rp:
            try:
                rp.cleanup()
            except Exception as e:
                Logger.error(f'Terminal: Error during final cleanup: {e}')
        if buzzer:
            try:
                buzzer.cleanup()
            except Exception as e:
                Logger.error(f'Terminal: Error during buzzer cleanup: {e}')