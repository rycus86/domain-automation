import time
import logging

from slackclient import SlackClient

from config import read_configuration
from metrics import Counter
from notifications import NotificationManager
from ssl_manager import SSLManager


logger = logging.getLogger('slack-notification')

messages_sent = Counter(
    'domain_automation_slack_sent',
    'The number of messages sent to Slack'
)
messages_failed = Counter(
    'domain_automation_slack_failed',
    'The number of messages failed to send to Slack'
)


class SlackNotificationManager(NotificationManager):
    def __init__(self):
        super(SlackNotificationManager, self).__init__()

        token = read_configuration(
            'SLACK_TOKEN', '/var/secrets/notifications'
        )

        self.channel = read_configuration(
            'SLACK_CHANNEL', '/var/secrets/notifications', 'general'
        )
        self.bot_name = read_configuration(
            'SLACK_BOT_NAME', '/var/secrets/notifications', 'domain-automation-bot'
        )
        self.bot_icon = read_configuration(
            'SLACK_BOT_ICON', '/var/secrets/notifications'
        )

        self.client = SlackClient(token)

    def send_update(self, update_type, subdomain, result):
        message = '`[%s update]` *%s* : %s' % (update_type, subdomain.full, result)
        
        self.send_message(message)

    def send_message(self, message, retry=1):
        if retry > 3:
            logger.error('Giving up on Slack message: %s' % message)
            return

        extras = {'icon_url': self.bot_icon} if self.bot_icon else {}

        response = self.client.api_call(
            'chat.postMessage',
            channel=self.channel,
            text=message,
            as_user=False,
            username=self.bot_name,
            **extras
        )

        if response['ok'] is False:
            messages_failed.inc()

            if 'Retry-After' in response['headers']:
                delay = int(response['headers']['Retry-After'])

                logger.debug('Retrying Slack message after %d seconds' % delay)

                time.sleep(delay)
                self.send_message(message, retry=retry + 1)

            else:
                logger.error('Failed to send message to Slack: %s' % message)

        else:
            logger.info('Slack message sent: %s' % message)

            messages_sent.inc()

    def dns_updated(self, subdomain, result):
        self.send_update('DNS', subdomain, result)

    def ssl_updated(self, subdomain, result):
        if result == SSLManager.RESULT_NOT_YET_DUE_FOR_RENEWAL:
            return

        self.send_update('SSL', subdomain, result)

    def message(self, text):
        self.send_message(text)
