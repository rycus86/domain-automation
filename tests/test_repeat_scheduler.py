import unittest

from scheduler.repeat import RepeatingScheduler


class MockScheduler(RepeatingScheduler):
    def __init__(self):
        super(RepeatingScheduler, self).__init__(self)

    def interval(self):
        return self.time


class RepeatingSchedulerTest(unittest.TestCase):
    def setUp(self):
        self.scheduler = RepeatingScheduler()

    def test_start_stop(self):
        invocations = [0]

        def invoke():
            invocations[0] += 1

        setattr(self.scheduler, 'interval', 5)
        self.scheduler.schedule(invoke)
        self.scheduler.cancel()

        self.assertEqual(invocations[0], 1)

