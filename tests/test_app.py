import os
import time
import socket
import unittest

import requests

import app
import factories

from datetime import datetime

from discovery import Discovery
from config import Subdomain
from dns_manager import DNSManager
from ssl_manager import SSLManager
from notifications import NotificationManager


class MockSubdomain(Subdomain):
    def __init__(self, name, base):
        super(MockSubdomain, self).__init__(name, base)
        self.current_ip = '1.1.1.1'
        self.cert_update = 0


class MockDiscovery(Discovery):
    def __init__(self, *bases, **kwargs):
        base = kwargs.pop('base', 'unit.test')

        self.subdomains = list(
            MockSubdomain(b, base) for b in bases
        )

    def _iter_subdomains(self):
        for subdomain in self.subdomains:
            yield subdomain


class MockDNSManager(DNSManager):
    def get_current_public_ip(self):
        return '1.2.3.4'

    def get_current_ip(self, subdomain):
        return subdomain.current_ip

    def update(self, subdomain, public_ip):
        subdomain.current_ip = public_ip
        return 'OK'


class MockSSLManager(SSLManager):
    def __init__(self):
        self.do_update = True

    def needs_update(self, subdomain):
        return self.do_update

    def update(self, subdomain):
        subdomain.cert_update = time.time()
        return 'Updated'


class MockNotificationManager(NotificationManager):
    def __init__(self):
        super(MockNotificationManager, self).__init__()
        self.events = list()

    def dns_updated(self, subdomain, result):
        self.events.append(('DNS', subdomain.name, result))

    def ssl_updated(self, subdomain, result):
        self.events.append(('SSL', subdomain.name, result))

    def message(self, text):
        self.events.append(('Message', text))


# noinspection PyUnresolvedReferences
class AppTest(unittest.TestCase):
    def setUp(self):
        self.discovery = MockDiscovery('www', 'test')
        self.dns = MockDNSManager()
        self.ssl = MockSSLManager()
        self.notifications = MockNotificationManager()
        self.scheduler = factories.get_scheduler()

        factories.get_discovery = lambda: self.discovery
        factories.get_dns_manager = lambda: self.dns
        factories.get_ssl_manager = lambda: self.ssl
        factories.get_notification_manager = lambda: self.notifications
        factories.get_scheduler = lambda: self.scheduler

        self.original_signal = app.signal.signal

    def tearDown(self):
        app.signal.signal = self.original_signal

    def test_main(self):        
        signals = dict()
        
        def mock_signal(signal, func):
            signals[signal] = func

        app.signal.signal = mock_signal

        app.main()

        current_ip = self.dns.get_current_public_ip()

        for subdomain in self.discovery.iter_subdomains():
            self.assertEqual(subdomain.current_ip, current_ip)
            self.assertGreater(subdomain.cert_update, 0)

        for message_type, message in self.notifications.events:
            if message_type == 'Message':
                self.assertIn('Application starting', message)
                self.assertIn('version: unknown', message)
                self.assertIn('built: %s' % datetime.fromtimestamp(0), message)
                break

        else:
            self.fail('Startup message not found')

        self.assertIn(('DNS', 'www', 'OK'), self.notifications.events)
        self.assertIn(('DNS', 'test', 'OK'), self.notifications.events)
        self.assertIn(('SSL', 'www', 'Updated'), self.notifications.events)
        self.assertIn(('SSL', 'test', 'Updated'), self.notifications.events)
        self.assertNotIn(('Message', 'Application exiting'), self.notifications.events)

        try:
            signals[app.signal.SIGTERM](app.signal.SIGTERM)
        except SystemExit:
            pass

        self.assertIn(('Message', 'Application exiting'), self.notifications.events)

    def test_skip_dns_update(self):
        class WWWUpdatingDNSManager(MockDNSManager):
            def get_current_ip(self, subdomain):
                if subdomain.name == 'www':
                    return '9.8.7.6'
                else:
                    return '1.2.3.4'

        self.dns = WWWUpdatingDNSManager()
        self.ssl.do_update = False

        app.main()

        for message_type, message in self.notifications.events:
            if message_type == 'Message':
                self.assertIn('Application starting', message)
                self.assertIn('version: unknown', message)
                self.assertIn('built: %s' % datetime.fromtimestamp(0), message)
                break

        else:
            self.fail('Startup message not found')

        self.assertIn(('DNS', 'www', 'OK'), self.notifications.events)
        self.assertNotIn(('DNS', 'test', 'OK'), self.notifications.events)
        self.assertEqual(len(self.notifications.events), 2)

    def test_skip_ssl_update(self):
        class NonChangingDNSManager(MockDNSManager):
            def get_current_ip(self, subdomain):
                return self.get_current_public_ip()

        class TestUpdatingSSLManager(MockSSLManager):
            def needs_update(self, subdomain):
                return subdomain.name == 'test'

        self.dns = NonChangingDNSManager()
        self.ssl = TestUpdatingSSLManager()

        app.main()

        for message_type, message in self.notifications.events:
            if message_type == 'Message':
                self.assertIn('Application starting', message)
                self.assertIn('version: unknown', message)
                self.assertIn('built: %s' % datetime.fromtimestamp(0), message)
                break

        else:
            self.fail('Startup message not found')

        self.assertIn(('SSL', 'test', 'Updated'), self.notifications.events)
        self.assertNotIn(('SSL', 'www', 'Updated'), self.notifications.events)
        self.assertEqual(len(self.notifications.events), 2)

    def test_failing_dns_notification(self):
        class FailingDNSManager(MockDNSManager):
            def update(self, subdomain, public_ip):
                if subdomain.name == 'test':
                    return 'Failed'
                else:
                    return super(FailingDNSManager, self).update(subdomain, public_ip)

        self.dns = FailingDNSManager()

        app.main()

        self.assertIn(('DNS', 'www', 'OK'), self.notifications.events)
        self.assertIn(('DNS', 'test', 'Failed'), self.notifications.events)

    def test_ignored_ssl_notification(self):
        class IgnoringSSLManager(MockSSLManager):
            def update(self, subdomain):
                if subdomain.name == 'www':
                    return 'Ignored'
                else:
                    return super(IgnoringSSLManager, self).update(subdomain)

        self.ssl = IgnoringSSLManager()

        app.main()

        self.assertIn(('SSL', 'www', 'Ignored'), self.notifications.events)
        self.assertIn(('SSL', 'test', 'Updated'), self.notifications.events)

    def test_multiple_notification_managers(self):
        events = list()

        class RecordingNotificationManager(NotificationManager):
            def __init__(self, prefix):
                super(RecordingNotificationManager, self).__init__()
                self.prefix = prefix

            def dns_updated(self, subdomain, result):
                events.append(('%s_DNS' % self.prefix, subdomain.name, result))

            def ssl_updated(self, subdomain, result):
                events.append(('%s_SSL' % self.prefix, subdomain.name, result))

        self.notifications = NotificationManager(
            RecordingNotificationManager('X'),
            RecordingNotificationManager('Y')
        )

        app.main()

        self.assertIn(('X_DNS', 'www', 'OK'), events)
        self.assertIn(('X_DNS', 'test', 'OK'), events)
        self.assertIn(('X_SSL', 'www', 'Updated'), events)
        self.assertIn(('X_SSL', 'test', 'Updated'), events)
        self.assertIn(('Y_DNS', 'www', 'OK'), events)
        self.assertIn(('Y_DNS', 'test', 'OK'), events)
        self.assertIn(('Y_SSL', 'www', 'Updated'), events)
        self.assertIn(('Y_SSL', 'test', 'Updated'), events)

    def test_notifications_with_errors(self):
        class FailingDNSManager(MockDNSManager):
            def update(self, subdomain, public_ip):
                raise Exception('DNS update failed')

        class FailingSSLManager(MockSSLManager):
            def update(self, subdomain):
                raise Exception('SSL update failed')

        self.dns = FailingDNSManager()
        self.ssl = FailingSSLManager()

        app.main()

        self.assertIn(('DNS', 'www', 'Failed: DNS update failed'), self.notifications.events)
        self.assertIn(('SSL', 'www', 'Failed: SSL update failed'), self.notifications.events)
        self.assertIn(('DNS', 'test', 'Failed: DNS update failed'), self.notifications.events)
        self.assertIn(('SSL', 'test', 'Failed: SSL update failed'), self.notifications.events)

    def test_suppress_notification_errors(self):
        messages = list()

        class RecordingNotificationManager(NotificationManager):
            def message(self, text):
                messages.append(text)

        class FailingNotificationManager(NotificationManager):
            def message(self, text):
                raise Exception('oops')

        self.notifications = NotificationManager(
            FailingNotificationManager(), RecordingNotificationManager()
        )

        app.main()

        self.assertEqual(len(messages), 1)
        self.assertIn('Application starting', messages[0])

    def test_metrics(self):
        port = self._get_free_tcp_port()

        os.environ['METRICS_HOST'] = 'localhost'
        os.environ['METRICS_PORT'] = str(port)

        self.addCleanup(os.environ.pop, 'METRICS_HOST', None)
        self.addCleanup(os.environ.pop, 'METRICS_PORT', None)

        app.main()

        metrics = requests.get('http://localhost:%d/metrics' % port).text

        # process / platform
        self.assertIn('python_info{', metrics)
        self.assertIn('process_start_time_seconds ', metrics)

        # app info
        self.assertIn('domain_automation_app_info{version=', metrics)
        self.assertIn('domain_automation_app_built_at ', metrics)

        # discovery
        self.assertIn('domain_automation_discovery_subdomains 2.0', metrics)

    @staticmethod
    def _get_free_tcp_port():
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(('localhost', 0))
        _, port = tcp.getsockname()
        tcp.close()

        return port
