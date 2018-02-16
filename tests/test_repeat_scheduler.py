import os
import time
import unittest

from scheduler.repeat import RepeatingScheduler


class MockScheduler(RepeatingScheduler):
    def __init__(self):
        super(MockScheduler, self).__init__()
        self.time = 5

    @property
    def interval(self):
        return self.time


class RepeatingSchedulerTest(unittest.TestCase):
    def setUp(self):
        self.scheduler = MockScheduler()
        self.invocations = 0

    def tearDown(self):
        os.environ.pop('IMMEDIATE_START', None)
        self.scheduler.cancel()

    def _invoke(self):
        self.invocations += 1

    def test_start_stop(self):
        self.scheduler.time = 0.05

        self.scheduler.schedule(self._invoke)

        self.assertEqual(self.invocations, 0)

        time.sleep(0.1)

        self.assertGreater(self.invocations, 0)

        time.sleep(0.1)

        self.assertGreater(self.invocations, 1)

        current = self.invocations

        self.scheduler.cancel()

        time.sleep(0.1)

        self.assertEqual(self.invocations, current)

    def test_continues_after_errors(self):
        def error(message, **kwargs):
            self._invoke()
            raise Exception('oops: %s %s' % (message, kwargs))

        self.scheduler.time = 0.05

        self.scheduler.schedule(error, 'failed', issue='forced')

        time.sleep(0.1)

        self.assertGreater(self.invocations, 0)

        time.sleep(0.1)

        self.assertGreater(self.invocations, 1)

    def test_immediate_start(self):
        os.environ['IMMEDIATE_START'] = 'Yes'

        self.scheduler = MockScheduler()
        self.scheduler.time = 0.05

        self.scheduler.schedule(self._invoke)

        self.assertGreater(self.invocations, 0)

        time.sleep(0.1)

        self.assertGreater(self.invocations, 1)

    def test_repeats(self):
        self.scheduler.time = 0.1
        self.scheduler.schedule(self._invoke)

        time.sleep(0.5)

        self.scheduler.cancel()

        self.assertAlmostEqual(self.invocations, 5, delta=1)
