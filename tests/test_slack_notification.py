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


class SlackNotificationTest(unittest.TestCase):
    def setUp(self):
        self.original_sleep = slack_message.time.sleep
        self.client = MockSlackClient(self)
        self.manager = slack_message.SlackNotificationManager()
        self.manager.channel = 'unittest'
        self.manager.client = self.client

    def tearDown(self):
        slack_message.time.sleep = self.original_sleep

    def test_dns_update(self):
        message = '`[DNS update]` *dns.update.test* : OK, test'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.dns_updated(Subdomain('dns', 'update.test'), 'OK, test')

        self.client.assert_call('chat.postMessage', channel='unittest', text=message)

        self.assertEqual(len(logs.output), 1)
        self.assertEqual(
            logs.output[0],
            'INFO:slack-notification:Slack message sent: %s' % message
        )

    def test_ssl_update(self):
        message = '`[SSL update]` *ssl.update.test* : Testing'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.ssl_updated(Subdomain('ssl', 'update.test'), 'Testing')

        self.client.assert_call('chat.postMessage', channel='unittest', text=message)

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

        slack_message.time.sleep = lambda x: x

        message = '`[DNS update]` *retry.update.test* : With retries'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.dns_updated(Subdomain('retry', 'update.test'), 'With retries')

        self.client.assert_call('chat.postMessage', channel='unittest', text=message)

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
        slack_message.time.sleep = lambda x: x

        message = '`[DNS update]` *give.up.update.test* : Failing'

        with self.assertLogs('slack-notification', 'DEBUG') as logs:
            self.manager.dns_updated(Subdomain('give.up', 'update.test'), 'Failing')

        self.client.assert_call('chat.postMessage', channel='unittest', text=message)

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
