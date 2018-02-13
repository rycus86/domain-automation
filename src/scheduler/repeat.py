import abc
import threading

from scheduler import Scheduler


class RepeatingScheduler(Scheduler):
    def __init__(self):
        self.timer = threading.Timer(self.interval, self._run)
        self.job = None
        self.cancelled = False

    def schedule(self, func, *args, **kwargs):
        self.job = (func, args, kwargs)

        if not self.cancelled:
            self.timer.start()

    def _run(self):
        if self.cancelled:
            return

        if not self.job:
            return

        func, args, kwargs = self.job

        if not self.cancelled:
            func(*args, **kwargs)

        self.timer = threading.Timer(self.interval, self._run)

        if not self.cancelled:
            self.timer.start()

    def cancel(self):
        self.cancelled = True
        self.timer.cancel()

    @abc.abstractproperty
    def interval(self):
        raise NotImplementedError('%s.interval not implemented' % type(self).__name__)


class FiveMinutesScheduler(RepeatingScheduler):
    def interval(self):
        return 5 * 60

