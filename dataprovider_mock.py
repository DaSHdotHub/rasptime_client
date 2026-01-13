from kivy.logger import Logger
import time


class DataProvider:
    """
    Mock DataProvider for testing without backend server
    All API calls are simulated and logged to console
    """

    def __init__(self, hostname, port, terminal_id, api_key):
        """
        Initialize mock data provider
        :param hostname: server hostname (not used in mock)
        :param port: server port (not used in mock)
        :param terminal_id: terminal ID (not used in mock)
        :param api_key: API key (not used in mock)
        """
        self.hostname = hostname
        self.port = port
        self.terminal_id = terminal_id
        self.api_key = api_key
        
        Logger.info('DataProvider: Running in MOCK MODE')
        Logger.info(f'DataProvider: Would connect to {hostname}:{port}')
        
        # Mock user database
        self.mock_users = {
            '12345': {
                'name': 'Max Mustermann',
                'image': 'images/default_user.jpeg',
                'id': 'user_001',
                'clocked_in': False
            },
            '67890': {
                'name': 'Anna Schmidt',
                'image': 'images/default_user.jpeg',
                'id': 'user_002',
                'clocked_in': False
            },
            '11111': {
                'name': 'Tom Meyer',
                'image': 'images/default_user.jpeg',
                'id': 'user_003',
                'clocked_in': True
            }
        }

    def working_users(self):
        """
        Mock: Get list of currently working users
        :return: list of tuples (name, clock_in_time, user_id)
        """
        Logger.info('API CALL: GET /working_users')
        
        working = []
        for uid, user in self.mock_users.items():
            if user['clocked_in']:
                clock_in_time = time.strftime('%H:%M', time.localtime())
                working.append((user['name'], clock_in_time, user['id']))
        
        Logger.info(f'API RESPONSE: {len(working)} users working')
        return working

    def user_info(self, tag):
        """
        Mock: Get user info by RFID tag
        :param tag: RFID tag UID
        :return: tuple (name, image_path, user_id) or None
        """
        Logger.info(f'API CALL: GET /user_info?tag={tag}')
        
        if tag in self.mock_users:
            user = self.mock_users[tag]
            result = (user['name'], user['image'], user['id'])
            Logger.info(f'API RESPONSE: User found - {user["name"]}')
            return result
        else:
            Logger.warning(f'API RESPONSE: User not found for tag {tag}')
            return None

    def user_work_summary(self, user_id):
        """
        Mock: Get user work summary
        :param user_id: user ID
        :return: tuple (today_minutes, week_minutes, last_week_minutes, vacation_days)
        """
        Logger.info(f'API CALL: GET /user_work_summary?user_id={user_id}')
        
        # Mock data: random work hours
        import random
        today = random.randint(0, 480)  # 0-8 hours in minutes
        week = random.randint(today, 2400)  # Up to 40 hours
        last_week = random.randint(1800, 2400)  # 30-40 hours
        vacation = random.randint(15, 30)  # 15-30 days
        
        result = (today, week, last_week, vacation)
        Logger.info(f'API RESPONSE: Work summary - Today: {today}min, Week: {week}min')
        return result

    def clock_in(self, user_id):
        """
        Mock: Clock in user
        :param user_id: user ID
        :return: True if successful, False if already clocked in, None on error
        """
        Logger.info(f'API CALL: POST /clock_in')
        Logger.info(f'API DATA: {{user_id: {user_id}, terminal_id: {self.terminal_id}}}')
        
        # Find user by ID
        for uid, user in self.mock_users.items():
            if user['id'] == user_id:
                if user['clocked_in']:
                    Logger.warning('API RESPONSE: User already clocked in')
                    return False
                else:
                    user['clocked_in'] = True
                    Logger.info('API RESPONSE: Clock in successful')
                    return True
        
        Logger.error(f'API RESPONSE: User {user_id} not found')
        return None

    def clock_out(self, user_id):
        """
        Mock: Clock out user
        :param user_id: user ID
        :return: True if successful, False if already clocked out, None on error
        """
        Logger.info(f'API CALL: POST /clock_out')
        Logger.info(f'API DATA: {{user_id: {user_id}, terminal_id: {self.terminal_id}}}')
        
        # Find user by ID
        for uid, user in self.mock_users.items():
            if user['id'] == user_id:
                if not user['clocked_in']:
                    Logger.warning('API RESPONSE: User already clocked out')
                    return False
                else:
                    user['clocked_in'] = False
                    Logger.info('API RESPONSE: Clock out successful')
                    return True
        
        Logger.error(f'API RESPONSE: User {user_id} not found')
        return None