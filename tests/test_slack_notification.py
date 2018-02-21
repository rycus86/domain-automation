import unittest

from config import Subdomain
from ssl_manager import SSLManager
from notifications import slack_message


class MockSlackClient(object):
    def __init__(self, test_case):
        self.test_case = test_case
        self.response = {'ok': True}
        self.last_call = None

    def api_call(self, *args, **kwargs):
        self.last_call = (args, kwargs)
        return self.response

    def assert_call(self, *args, **kwargs):
        self.test_case.assertEqual(self.last_call, (args, kwargs))


class MockLogContext(object):
    def __init__(self, name):
        self.name = name
        self.output = list()

        self.original_logger_debug = slack_message.logger.debug
        self.original_logger_info = slack_message.logger.info
        self.original_logger_error = slack_message.logger.error

    def __enter__(self):
        def log(level, message):
            self.output.append('%s:%s:%s' % (level, self.name, message))

        slack_message.logger.debug = lambda m: log('DEBUG', m)
        slack_message.logger.info = lambda m: log('INFO', m)
        slack_message.logger.error = lambda m: log('ERROR', m)
        
        return self

    def __exit__(self, *args, **kwargs):
        slack_message.logger.debug = self.original_logger_debug
        slack_message.logger.info = self.original_logger_info
        slack_message.logger.error = self.original_logger_error


class MockTimer(object):
    def __init__(self, _, func, args=None, kwargs=None):
        self.function = func
        self.args = args
        self.kwargs = kwargs

    def setDaemon(self, _):
        pass

    def start(self):
        self.function(*self.args, **self.kwargs)


class SlackNotificationTest(unittest.TestCase):
    def setUp(self):
        self.original_timer = slack_message.threading.Timer
        self.client = MockSlackClient(self)
        self.manager = slack_message.SlackNotificationManager()
        self.manager.channel = 'unittest'
        self.manager.bot_name = 'test-bot'
        self.manager.client = self.client

        if not hasattr(self, 'assertLogs'):
            setattr(self, 'assertLogs', self._assert_logs)

    def tearDown(self):
        slack_message.threading.Timer = self.original_timer

    def _assert_logs(self, name, level):
        return MockLogContext(name)

    def test_message(self):
        message = 'Sample notification message'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.message(message)

        self.client.assert_call(
            'chat.postMessage', channel='unittest', text=message,
            as_user=False, username='test-bot'
        )

        self.assertEqual(len(logs.output), 1)
        self.assertEqual(
            logs.output[0],
            'INFO:slack-notification:Slack message sent: %s' % message
        )

    def test_dns_update(self):
        message = '`[DNS update]` *dns.update.test* : OK, test'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.dns_updated(Subdomain('dns', 'update.test'), 'OK, test')

        self.client.assert_call(
            'chat.postMessage', channel='unittest', text=message,
            as_user=False, username='test-bot'
        )

        self.assertEqual(len(logs.output), 1)
        self.assertEqual(
            logs.output[0],
            'INFO:slack-notification:Slack message sent: %s' % message
        )

    def test_ssl_update(self):
        message = '`[SSL update]` *ssl.update.test* : Testing'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.ssl_updated(Subdomain('ssl', 'update.test'), 'Testing')

        self.client.assert_call(
            'chat.postMessage', channel='unittest', text=message,
            as_user=False, username='test-bot'
        )

        self.assertEqual(len(logs.output), 1)
        self.assertEqual(
            logs.output[0],
            'INFO:slack-notification:Slack message sent: %s' % message
        )

    def test_skip_ssl_notification(self):
        self.manager.ssl_updated(
            Subdomain('skip', 'cert.renewal'),
            SSLManager.RESULT_NOT_YET_DUE_FOR_RENEWAL
        )

        self.assertIsNone(self.client.last_call)

    def test_retry_once(self):
        original_send_message = self.manager.send_message

        def send_message(*args, **kwargs):
            if kwargs.get('retry', 1) > 1:
                self.client.response = {'ok': True}
            else:
                self.client.response = {'ok': False, 'headers': {'Retry-After': '12'}}

            original_send_message(*args, **kwargs)

        self.manager.send_message = send_message

        # slack_message.time.sleep = lambda x: x
        slack_message.threading.Timer = MockTimer

        message = '`[DNS update]` *retry.update.test* : With retries'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.dns_updated(Subdomain('retry', 'update.test'), 'With retries')

        self.client.assert_call(
            'chat.postMessage', channel='unittest', text=message,
            as_user=False, username='test-bot'
        )

        self.assertEqual(len(logs.output), 2)
        self.assertEqual(
            logs.output[0],
            'DEBUG:slack-notification:Retrying Slack message after 12 seconds'
        )
        self.assertEqual(
            logs.output[1],
            'INFO:slack-notification:Slack message sent: %s' % message
        )

    def test_give_up_retries(self):
        self.client.response = {'ok': False, 'headers': {'Retry-After': '3'}}

        # slack_message.time.sleep = lambda x: x
        slack_message.threading.Timer = MockTimer

        message = '`[DNS update]` *give.up.update.test* : Failing'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.dns_updated(Subdomain('give.up', 'update.test'), 'Failing')

        self.client.assert_call(
            'chat.postMessage', channel='unittest', text=message,
            as_user=False, username='test-bot'
        )

        self.assertEqual(len(logs.output), 4)

        for idx in range(3):
            self.assertEqual(
                logs.output[idx],
                'DEBUG:slack-notification:Retrying Slack message after 3 seconds'
            )

        self.assertEqual(
            logs.output[3],
            'ERROR:slack-notification:Giving up on Slack message: %s' % message
        )
