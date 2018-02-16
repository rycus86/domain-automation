import time
import unittest

from scheduler.repeat_docker import DockerAwareScheduler


class DockerAwareSchedulerTest(unittest.TestCase):
    def setUp(self):
        self.scheduler = DockerAwareScheduler()
        self.scheduler.immediate_start = True
        self.runs = list()

    def test_start_stop(self):
        self.scheduler.schedule(self.signal)
        self.scheduler.cancel()

        self.assert_events(1)

    def test_event(self):
        original_events = self.scheduler.client.events

        def no_events(*args, **kwargs):
            yield None

        def mock_events(*args, **kwargs):
            yield {'type': 'example'}
            yield {
                'scope': 'swarm', 'Action': 'create',
                'Type': 'service', 'Actor': {'name': 'sample'}
            }
            yield {'type': 'not.interesting'}

            self.scheduler.client.events = no_events

        self.scheduler.client.events = mock_events

        try:
            self.scheduler.schedule(self.signal)

            time.sleep(0.2)

            self.scheduler.cancel()

            self.assert_events(2)

        finally:
            self.scheduler.client.events = original_events

    def signal(self):
        self.runs.append('run')

    def assert_events(self, count):
        self.assertEqual(len(self.runs), count)
        self.assertEqual(self.runs, ['run'] * count)
