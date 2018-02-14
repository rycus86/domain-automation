import os
import sys
import time
import logging
import argparse

import docker
from docker.types.services import ServiceMode, RestartPolicy

from docker_helper import get_current_container_id

from config import read_configuration
from notifications import NotificationManager


logger = logging.getLogger('docker-signal')


def send_signal(client, label):
    for container in client.containers.list(filters={'label': label}):
        signal = container.labels.get(label)

        if signal:
            logger.info('Signalling %s [%s] - %s' % (container.name, container.id, signal)) 

            container.kill(signal)


class DockerSignalNotification(NotificationManager):
    def __init__(self):
        super(DockerSignalNotification, self).__init__()

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
        
        image = current_container.attrs['Config'].get('Image')
        if not image:
            return

        command = [
            sys.executable, __file__, '--label', self.label_name
        ]

        log_driver = current_container.attrs['HostConfig']['LogConfig']['Type']
        log_config = current_container.attrs['HostConfig']['LogConfig']['Config']

        sender = self.client.services.create(
            image, command=command,
            env=['PYTHONPATH=%s' % os.environ.get('PYTHONPATH', '.')],
            log_driver=log_driver, log_driver_options=log_config,
            mode=ServiceMode('global'), 
            restart_policy=RestartPolicy(condition='none', max_attempts=0),
            mounts=['/var/run/docker.sock:/var/run/docker.sock:ro']
        )

        max_wait = 60
        start_time = time.time()

        while abs(time.time() - start_time) < max_wait:
            if all(task['DesiredState'] == 'shutdown' for task in sender.tasks()):
                break

            time.sleep(1)

        states = list(task['Status']['State'] for task in sender.tasks())
        logs = ''.join(
            item.decode() if hasattr(item, 'decode') else item
            for item in sender.logs(stdout=True, stderr=True)
        ).strip()

        sender.remove()

        logger.info(
            'Signalled containers with label %s - result: %s' % 
            (self.label_name, ', '.join(map(str, states)))
        )

        if logs:
            logger.info('Signal logs: %s' % logs)


def main(client, args=sys.argv[1:]):
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')

    parser = argparse.ArgumentParser(description='Docker signal sender')
    parser.add_argument('--label', required=True, help='The target container label name')

    arguments = parser.parse_args(args)

    send_signal(client, arguments.label)


if __name__ == '__main__':
    main(docker.from_env())
