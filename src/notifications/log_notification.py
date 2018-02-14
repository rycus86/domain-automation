import logging

from notifications import NotificationManager


logger = logging.getLogger('log-notification')


class LoggingNotificationManager(NotificationManager):
    def dns_updated(self, subdomain, result):
        if result.startswith('OK'):
            logger.info('[DNS] %s : %s' % (subdomain.full, result))
        else:
            logger.error('[DNS] %s : %s' % (subdomain.full, result))

    def ssl_updated(self, subdomain, result):
        if 'failed' in result.lower():
            logger.error('[SSL] %s : %s' % (subdomain.full, result))
        else:
            logger.info('[SSL] %s : %s' % (subdomain.full, result))

    def message(self, text):
        logger.info(text)
