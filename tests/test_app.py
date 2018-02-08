import time
import unittest

import app
import factories

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
    def __init__(self, *bases, base='unit.test'):
        self.subdomains = list(
            MockSubdomain(b, base) for b in bases
        )

    def iter_subdomains(self):
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


# noinspection PyUnresolvedReferences
class AppTest(unittest.TestCase):
    def setUp(self):
        self.discovery = MockDiscovery('www', 'test')
        self.dns = MockDNSManager()
        self.ssl = MockSSLManager()
        self.notifications = MockNotificationManager()

        factories.get_discovery = lambda: self.discovery
        factories.get_dns_manager = lambda: self.dns
        factories.get_ssl_manager = lambda: self.ssl
        factories.get_notification_manager = lambda: self.notifications

    def test_main(self):
        app.main()

        current_ip = self.dns.get_current_public_ip()

        for subdomain in self.discovery.iter_subdomains():
            self.assertEqual(subdomain.current_ip, current_ip)
            self.assertGreater(subdomain.cert_update, 0)

        self.assertIn(('DNS', 'www', 'OK'), self.notifications.events)
        self.assertIn(('DNS', 'test', 'OK'), self.notifications.events)
        self.assertIn(('SSL', 'www', 'Updated'), self.notifications.events)
        self.assertIn(('SSL', 'test', 'Updated'), self.notifications.events)

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

        self.assertIn(('DNS', 'www', 'OK'), self.notifications.events)
        self.assertNotIn(('DNS', 'test', 'OK'), self.notifications.events)
        self.assertEqual(len(self.notifications.events), 1)

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

        self.assertIn(('SSL', 'test', 'Updated'), self.notifications.events)
        self.assertNotIn(('SSL', 'www', 'Updated'), self.notifications.events)
        self.assertEqual(len(self.notifications.events), 1)

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
