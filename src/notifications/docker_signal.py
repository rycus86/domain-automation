import sys
import logging
import argparse

import docker

from docker_helper import get_current_container_id, read_configuration

from notifications import NotificationManager


logger = logging.getLogger('docker-signal')


def send_signal(client, label):
    for container in client.containers.list(filters={'label': label}):
        signal = container.labels.get(label)

        if signal:
            logger.info('Signalling %s [%s] - %s' % (container.name, container.id)) 

            container.kill(signal)


class DockerSignalNotification(NotificationManager):
    def __init__(self):
        self.client = docker.from_env()
        self.label_name = read_configuration(
            'DOCKER_SIGNAL_LABEL', '/var/secrets/notifications', 'domain.automation.signal'
        )

    def ssl_updated(self, subdomain, result):
        if not result or not result.startswith('OK'):
            return

        if len(self.client.swarm.attrs) > 0:
            self._send_signal_in_swarm()

        else:
            send_signal(self.client, self.label_name)

    def _send_signal_in_swarm(self):
        current_container_id = get_current_container_id()
        if not current_container_id:
            return

        current_container = self.client.containers.get(current_container_id)
        if not current_container:
            return
        
        image = container.attrs['Config'].get('Image')
        if not image:
            return

        pass  # TODO start a global service with no restart policy, wait for finish and remove


def main(client, args=sys.argv[1:]):
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')

    parser = argparse.ArgumentParser(description='Docker signal sender')
    parser.add_argument('--label', required=True, help='The target container label name')

    arguments = parser.parse_args(args)

    send_signal(client, arguments.label)


if __name__ == '__main__':
    main(docker.from_env())

