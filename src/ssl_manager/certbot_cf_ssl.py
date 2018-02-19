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
        super(CertbotCloudflareSSLManager, self).__init__()

        self.cf_email = read_configuration('CLOUDFLARE_EMAIL', '/var/secrets/cloudflare')
        self.cf_token = read_configuration('CLOUDFLARE_TOKEN', '/var/secrets/cloudflare')

        self.dns_propagation_seconds = read_configuration(
            'DNS_PROPAGATION_SECONDS', '/var/secrets/certbot', default='30'
        )

        self.certbot_email = read_configuration(
            'CERTBOT_EMAIL', '/var/secrets/certbot', default=self.cf_email
        )
        self.certbot_timeout = int(read_configuration(
            'CERTBOT_TIMEOUT', '/var/secrets/certbot', '120'
        ))
        self.use_staging = read_configuration(
            'CERTBOT_STAGING', '/var/secrets/certbot', default='no'
        ).lower() in ('yes', 'true', '1')


    def needs_update(self, subdomain):
        return True  # we'll use 'certonly' with '--keep'

    def update(self, subdomain):
        try:
            with open('.cloudflare.ini', 'w') as cloudflare_config:
                cloudflare_config.write('dns_cloudflare_email = %s\n' % self.cf_email)
                cloudflare_config.write('dns_cloudflare_api_key = %s\n' % self.cf_token)

            os.chmod('.cloudflare.ini', 0o400)

            logger.info('Processing SSL certificates for %s ...' % subdomain.full)

            command = [
                    'certbot', 'certonly', '-n', '--keep',
                    '-d', subdomain.full,
                    '--dns-cloudflare',
                    '--dns-cloudflare-credentials', '.cloudflare.ini',
                    '--dns-cloudflare-propagation-seconds', str(self.dns_propagation_seconds),
                    '--email', self.certbot_email, '--agree-tos'
                ]

            if self.use_staging:
                command.append('--staging')

            result = self.subprocess_run(
                command,
                timeout=self.certbot_timeout, universal_newlines=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            if result.returncode != 0:
                if result.stdout:
                    logger.info(result.stdout)

                if result.stderr:
                    logger.error(result.stderr)

                return 'Failed with exit code: %s' % result.returncode

            if result.stdout:
                logger.debug(result.stdout)

            if result.stderr:
                logger.debug(result.stderr)

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

    def subprocess_run(self, command, **kwargs):
        if hasattr(subprocess, 'run'):
            return subprocess.run(command, **kwargs)

        else:
            del kwargs['timeout']

            process = subprocess.Popen(command, **kwargs)

            returncode = process.wait()
            stdout, stderr = process.communicate()

            class ProcessResult(object):
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            return ProcessResult(returncode, stdout, stderr)

