import logging
import threading

from datetime import datetime, timedelta

import docker

import factories

from scheduler.repeat import FiveMinutesScheduler


logger = logging.getLogger('docker-scheduler')


class DockerAwareScheduler(FiveMinutesScheduler):
    def __init__(self):
        super(DockerAwareScheduler, self).__init__()
        self.notifications = factories.get_notification_manager()
        self.client = docker.from_env()
        self.thread = threading.Thread(target=self.listen_for_events)

    def schedule(self, func, *args, **kwargs):
        super(DockerAwareScheduler, self).schedule(func, *args, **kwargs)
        self.thread.start()

    def listen_for_events(self):
        since = datetime.utcnow()

        while not self.cancelled:
            until = datetime.utcnow() + timedelta(seconds=5)

            self.process_events(since=since, until=until)

            since = until

    def process_events(self, since, until):
        for event in self.client.events(decode=True, since=since, until=until):
            if self.cancelled:
                break

            if not event:
                continue

            scope, action, event_type, actor = map(
                event.get, ('scope', 'Action', 'Type', 'Actor')
            )

            if (scope, event_type, action) != ('swarm', 'service', 'create'):
                continue

            if actor:
                name = actor.get('Attributes', dict()).get('name', 'unknown')

            else:
                name = 'unknown'

            self.notifications.message('Service created: %s' % name)

            self._run()

    def cancel(self):
        super(DockerAwareScheduler, self).cancel()
        self.thread.join(timeout=10)
        self.client.api.close()
