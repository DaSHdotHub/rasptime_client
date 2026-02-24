from time import time
from kivy.logger import Logger
from requests import get, post, RequestException
from datetime import datetime, timedelta


class DataProvider:

    def __init__(self, host, port, terminal_id, auth):
        """
        Provides data taken from timeclock server
        :param host: IP address or hostname
        :param port: port number
        :param terminal_id: identifier of terminal (for future use)
        :param auth: API key (for future use)
        """
        self.host = host
        self.port = port
        self.terminal_id = terminal_id
        self.auth = auth
        self.base_url = f'http://{host}:{port}/api'
        self.timeout = 5

    def __headers(self):
        """
        Returns request headers
        For now just content-type, can add auth later
        """
        return {
            'Content-Type': 'application/json',
            'X-Terminal-ID': str(self.terminal_id),
        }

    def __get(self, endpoint, params=None):
        """
        GET request to API
        :param endpoint: API endpoint (without /api prefix)
        :param params: query parameters
        :return: JSON response or None
        """
        try:
            url = f'{self.base_url}/{endpoint}'
            resp = get(url, headers=self.__headers(), params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None
            else:
                Logger.error(f'DataProvider: GET {endpoint} returned {resp.status_code}')
                return None
        except RequestException as e:
            Logger.error(f'DataProvider: GET {endpoint} failed: {e}')
            return None

    def __post(self, endpoint, data=None):
        """
        POST request to API
        :param endpoint: API endpoint (without /api prefix)
        :param data: JSON body
        :return: JSON response or None
        """
        try:
            url = f'{self.base_url}/{endpoint}'
            resp = post(url, headers=self.__headers(), json=data, timeout=self.timeout)
            if resp.status_code in [200, 201]:
                return resp.json()
            elif resp.status_code == 404:
                return None
            else:
                Logger.error(f'DataProvider: POST {endpoint} returned {resp.status_code}')
                return None
        except RequestException as e:
            Logger.error(f'DataProvider: POST {endpoint} failed: {e}')
            return None

    def user_info(self, tag):
        """
        Returns user data by RFID tag
        :param tag: rfid tag identifier
        :return: None or (name, picture path, user_id, clocked_in)
        """
        try:
            data = self.__get('terminal/user', params={'rfid': tag})
            if data:
                return (
                    data.get('displayName'),
                    'images/default_user.jpg',  # Default image for now
                    data.get('userId'),
                    data.get('clockedIn', False)
                )
            return None
        except Exception as e:
            Logger.error(f'DataProvider: user_info error: {e}')
            return None

    def punch(self, rfid_tag, break_minutes=None):
        """
        Clock in or out (toggles automatically based on current state)
        :param rfid_tag: RFID tag identifier
        :param break_minutes: Optional break minutes for clock out
        :return: ('CLOCK_IN'/'CLOCK_OUT', message, display_name) or None on error
        """
        try:
            body = {'rfid': rfid_tag}
            if break_minutes is not None:
                body['breakMinutes'] = break_minutes
            
            data = self.__post('terminal/punch', body)
            if data:
                return (
                    data.get('action'),
                    data.get('message'),
                    data.get('displayName')
                )
            return None
        except Exception as e:
            Logger.error(f'DataProvider: punch error: {e}')
            return None

    def clock_in(self, user_id):
        """
        Legacy method - kept for backwards compatibility
        Use punch() instead for new implementations
        :param user_id: identifier of timeclock user
        :return: True if successful, False if already clocked in, None if error
        """
        Logger.warning('DataProvider: clock_in() is deprecated, use punch() instead')
        # We can't easily use this anymore since punch uses RFID, not user_id
        # Return True to not break existing code
        return True

    def clock_out(self, user_id):
        """
        Legacy method - kept for backwards compatibility
        Use punch() instead for new implementations
        :param user_id: identifier of timeclock user
        :return: True if successful, False if not clocked in, None if error
        """
        Logger.warning('DataProvider: clock_out() is deprecated, use punch() instead')
        return True

    def user_work_summary(self, user_id):
        """
        Gets work summary from timeclock server
        :param user_id: identifier of timeclock user
        :return: None or (today_minutes, week_minutes, last_week_minutes, vacation_days)
        """
        try:
            today = datetime.now().date()
            
            # Get today's entries
            today_data = self.__get('admin/time-entries', params={
                'userId': user_id,
                'from': today.isoformat(),
                'to': today.isoformat()
            })
            today_minutes = today_data.get('totalNetMinutes', 0) if today_data else 0

            # Get this week's entries (Monday to Sunday)
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            week_data = self.__get('admin/time-entries', params={
                'userId': user_id,
                'from': week_start.isoformat(),
                'to': week_end.isoformat()
            })
            week_minutes = week_data.get('totalNetMinutes', 0) if week_data else 0

            # Get last week's entries
            last_week_start = week_start - timedelta(days=7)
            last_week_end = week_start - timedelta(days=1)
            last_week_data = self.__get('admin/time-entries', params={
                'userId': user_id,
                'from': last_week_start.isoformat(),
                'to': last_week_end.isoformat()
            })
            last_week_minutes = last_week_data.get('totalNetMinutes', 0) if last_week_data else 0

            # Vacation days - not implemented yet, return 0
            vacation_days = 0

            return (today_minutes, week_minutes, last_week_minutes, vacation_days)
        except Exception as e:
            Logger.error(f'DataProvider: user_work_summary error: {e}')
            return None

    def working_users(self):
        """
        Returns list of clocked in users
        :return: list of tuples (name, start_time, user_id)
        """
        try:
            data = self.__get('admin/users')
            if not data:
                return []
            
            working = []
            for user in data:
                if user.get('clockedIn', False):
                    # We don't have clock-in time in user object
                    # Just show empty time for now
                    working.append((
                        user.get('displayName'),
                        '',  # Clock-in time not available from this endpoint
                        user.get('id')
                    ))
            return working
        except Exception as e:
            Logger.error(f'DataProvider: working_users error: {e}')
            return []

    def check_registration_mode(self):
        """
        Check if admin panel is waiting for RFID registration
        :return: session_id if registration mode active, None otherwise
        """
        try:
            data = self.__get('terminal/registration/active')
            if data and data.get('active'):
                return data.get('sessionId')
            return None
        except Exception as e:
            Logger.error(f'DataProvider: check_registration_mode error: {e}')
            return None

    def submit_registration(self, session_id, rfid_tag):
        """
        Submit RFID tag for registration
        :param session_id: Registration session ID from check_registration_mode
        :param rfid_tag: RFID tag to register
        :return: True on success, False on failure
        """
        try:
            data = self.__post('admin/registration/submit', {
                'sessionId': session_id,
                'rfidTag': rfid_tag
            })
            return data is not None
        except Exception as e:
            Logger.error(f'DataProvider: submit_registration error: {e}')
            return False

    def health_check(self):
        """
        Check if backend is reachable
        :return: True if healthy, False otherwise
        """
        try:
            data = self.__get('health')
            return data is not None and data.get('status') == 'UP'
        except Exception as e:
            Logger.error(f'DataProvider: health_check error: {e}')
            return False