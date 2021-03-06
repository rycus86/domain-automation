import os
import unittest
import subprocess

from datetime import datetime, timedelta

from config import Subdomain
from ssl_manager.certbot_cf_ssl import CertbotCloudflareSSLManager


class MockCompletedProcess(object):
    def __init__(self):
        self.args = []
        self.kwargs = {}
        self.stdout = ''
        self.stderr = ''
        self.returncode = 0


class CertbotCloudflareSSLManagerTest(unittest.TestCase):
    def setUp(self):
        self.mock_result = MockCompletedProcess()

        os.environ['CLOUDFLARE_EMAIL'] = 'unittest@cf.com'
        os.environ['CLOUDFLARE_TOKEN'] = 'cf001234'
        os.environ['CERTBOT_STAGING'] = 'no'

        self.manager = CertbotCloudflareSSLManager()
        self.manager.subprocess_run = self._mock_subprocess_run

    def _mock_subprocess_run(self, popen_args, **kwargs):
        result = self.mock_result
        result.args = popen_args
        result.kwargs = kwargs
        return result
    
    def tearDown(self):
        del os.environ['CLOUDFLARE_EMAIL']
        del os.environ['CLOUDFLARE_TOKEN']
        del os.environ['CERTBOT_STAGING']

    def test_new_certificate(self):
        self.mock_result.stdout = 'Congratulations! It worked!'
        self.mock_result.stderr = 'Obtaining a new certificate'

        result = self.manager.update(Subdomain('new-domain', 'unit.test'))
        
        self.assertEqual(result, 'OK, new certificate')

        self.assertIn('certbot certonly -n --keep', ' '.join(self.mock_result.args))
        self.assertIn('-d new-domain.unit.test', ' '.join(self.mock_result.args))
        self.assertIn('--email unittest@cf.com', ' '.join(self.mock_result.args))
        self.assertIn('--dns-cloudflare', ' '.join(self.mock_result.args))
        self.assertIn('--dns-cloudflare-credentials .cloudflare.ini', ' '.join(self.mock_result.args))
        self.assertIn('--dns-cloudflare-propagation-seconds 30', ' '.join(self.mock_result.args))

        self.assertIn(('timeout', 120), self.mock_result.kwargs.items())
        self.assertIn(('stdout', subprocess.PIPE), self.mock_result.kwargs.items())
        self.assertIn(('stderr', subprocess.PIPE), self.mock_result.kwargs.items())
        
        self.assertNotIn('--staging', self.mock_result.args)

    def test_existing_certificate(self):
        self.mock_result.stdout = 'Congratulations! It worked!'
        self.mock_result.stderr = 'Renewing an existing certificate'

        result = self.manager.update(Subdomain('existing-domain', 'unit.test'))
        
        self.assertEqual(result, 'OK, renewed')
        self.assertIn('-d existing-domain.unit.test', ' '.join(self.mock_result.args))

    def test_not_yet_due_for_renewal(self):
        self.mock_result.stdout = 'The certificate is not yet due for renewal, skipping.'

        result = self.manager.update(Subdomain('still-valid', 'unit.test'))
        
        self.assertEqual(result, 'Not yet due for renewal')
        self.assertIn('-d still-valid.unit.test', ' '.join(self.mock_result.args))

    def test_unknown_result(self):
        self.mock_result.stdout = 'Maybe Certbot got updated'

        result = self.manager.update(Subdomain('unknown', 'unit.test'))
        
        self.assertEqual(result, 'Unknown')
        self.assertIn('-d unknown.unit.test', ' '.join(self.mock_result.args))

    def test_repeat_scheduling(self):
        self.mock_result.stdout = 'Maybe Certbot got updated'
        subdomain1 = Subdomain('unknown-1', 'unit.test')
        subdomain2 = Subdomain('unknown-2', 'unit.test')

        self.assertTrue(self.manager.needs_update(subdomain1))
        result = self.manager.update(subdomain1)
        self.assertEqual(result, 'Unknown')

        self.assertTrue(self.manager.needs_update(subdomain2))
        result = self.manager.update(subdomain2)
        self.assertEqual(result, 'Unknown')

        self.assertFalse(self.manager.needs_update(subdomain1))
        self.assertFalse(self.manager.needs_update(subdomain2))

        self.manager.last_run[subdomain1.full] = datetime.now() - timedelta(seconds=6 * 60 * 60)

        self.assertFalse(self.manager.needs_update(subdomain1))
        self.assertFalse(self.manager.needs_update(subdomain2))

        self.manager.last_run[subdomain1.full] = datetime.now() - timedelta(days=0.5, seconds=30)

        self.assertTrue(self.manager.needs_update(subdomain1))
        result = self.manager.update(subdomain1)
        self.assertEqual(result, 'Unknown')

        self.assertFalse(self.manager.needs_update(subdomain1))

    def test_use_staging_servers(self):
        self.manager.use_staging = True

        self.manager.update(Subdomain('staging', 'unit.test'))

        self.assertIn('--staging', self.mock_result.args)

    def test_failing_certbot(self):
        self.mock_result.returncode = 1

        result = self.manager.update(Subdomain('failing.unit.test'))

        self.assertEqual(result, 'Failed with exit code: 1')

