import os
import logging
import subprocess

from config import read_configuration
from ssl_manager import SSLManager


logger = logging.getLogger('ssl-certbot-cloudflare')


class CertbotCloudflareSSLManager(SSLManager):
    MSG_NEW_CERT = 'Obtaining a new certificate'
    MSG_RENEW_CERT = 'Renewing an existing certificate'
    MSG_SUCCESSFUL = 'Congratulations!'
    MSG_NOT_YET_DUE = 'not yet due for renewal'

    def __init__(self):
        self.use_staging = False

    def needs_update(self, subdomain):
        return True  # we'll use 'certonly' with '--keep'

    def update(self, subdomain):
        try:
            cf_email = read_configuration('CLOUDFLARE_EMAIL', '/var/secrets/cloudflare')
            cf_token = read_configuration('CLOUDFLARE_TOKEN', '/var/secrets/cloudflare')

            certbot_email = read_configuration('CERTBOT_EMAIL', '/var/secrets/certbot', default=cf_email)
            dns_propagation_seconds = read_configuration(
                'DNS_PROPAGATION_SECONDS', '/var/secrets/certbot', default='10'
            )

            with open('.cloudflare.ini', 'w') as cloudflare_config:
                cloudflare_config.write('dns_cloudflare_email = %s\n' % cf_email)
                cloudflare_config.write('dns_cloudflare_api_key = %s\n' % cf_token)

            os.chmod('.cloudflare.ini', 0o400)

            logger.info('Processing SSL certificates for %s ...' % subdomain.full)

            command = [
                    'certbot', 'certonly', '-n', '--keep',
                    '-d', subdomain.full,
                    '--dns-cloudflare',
                    '--dns-cloudflare-credentials', '.cloudflare.ini',
                    '--dns-cloudflare-propagation-seconds', str(dns_propagation_seconds),
                    '--email', certbot_email, '--agree-tos'
                ]

            if self.use_staging:
                command.append('--staging')

            result = subprocess.run(
                command,
                timeout=60, universal_newlines=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            if result.stdout:
                logger.debug(result.stdout)

            if result.stderr:
                logger.debug(result.stderr)

            if result.returncode != 0:
                return 'Failed with exit code: %s' % result.returncode

            if self.MSG_SUCCESSFUL in result.stdout:
                if self.MSG_NEW_CERT in result.stdout or self.MSG_NEW_CERT in result.stderr:
                    return 'OK, new certificate'

                elif self.MSG_RENEW_CERT in result.stdout or self.MSG_RENEW_CERT in result.stderr:
                    return 'OK, renewed'

                else:
                    return 'OK'

            elif self.MSG_NOT_YET_DUE in result.stdout:
                return self.RESULT_NOT_YET_DUE_FOR_RENEWAL

            else:
                return 'Unknown'

        finally:
            if os.path.exists('.cloudflare.ini'):
                os.remove('.cloudflare.ini')
