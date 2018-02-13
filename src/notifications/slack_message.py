import time
import logging

from slackclient import SlackClient
from docker_helper import read_configuration

from ssl_manager import SSLManager
from notifications import NotificationManager


logger = logging.getLogger('slack-notification')


class SlackNotificationManager(NotificationManager):
    def __init__(self):
        super(SlackNotificationManager, self).__init__()

        token = read_configuration(
            'SLACK_TOKEN', '/var/secrets/notifications'
        )

        self.channel = read_configuration(
            'SLACK_CHANNEL', '/var/secrets/notifications', 'general'
        )

        self.client = SlackClient(token)

    def send_message(self, update_type, subdomain, result, retry=1):
        message = '`[%s update]` *%s* : %s' % (update_type, subdomain.full, result)

        if retry > 3:
            logger.error('Giving up on Slack message: %s' % message)
            return

        response = self.client.api_call(
            'chat.postMessage',
            channel=self.channel,
            text=message
        )

        if response['ok'] is False:
            if 'Retry-After' in response['headers']:
                delay = int(response['headers']['Retry-After'])

                logger.debug('Retrying Slack message after %d seconds' % delay)

                time.sleep(delay)
                self.send_message(update_type, subdomain, result, retry=retry + 1)

            else:
                logger.error('Failed to send message to Slack: %s' % message)

        else:
            logger.info('Slack message sent: %s' % message)

    def dns_updated(self, subdomain, result):
        self.send_message('DNS', subdomain, result)

    def ssl_updated(self, subdomain, result):
        if result == SSLManager.RESULT_NOT_YET_DUE_FOR_RENEWAL:
            return

        self.send_message('SSL', subdomain, result)
