import abc
import logging
import threading

from scheduler import Scheduler


logger = logging.getLogger('repeat-scheduler')


class RepeatingScheduler(Scheduler):
    lock = threading.Lock()

    def __init__(self):
        self.timer = None
        self.job = None
        self.cancelled = False

    def schedule(self, func, *args, **kwargs):
        self.job = (func, args, kwargs)

        with self.lock:
            if not self.cancelled:
                self.timer = threading.Timer(self.interval, self._run)
                self.timer.start()

    def _run(self):
        with self.lock:
            if self.cancelled:
                return

            if not self.job:
                return

            try:
                func, args, kwargs = self.job
                func(*args, **kwargs)

            except Exception as ex:
                logger.error('Failed to execute the scheduled task', exc_info=ex)

        with self.lock:
            if not self.cancelled:
                self.timer = threading.Timer(self.interval, self._run)
                self.timer.start()

    def cancel(self):
        with self.lock:
            self.cancelled = True
            self.timer.cancel()

    @property
    @abc.abstractmethod
    def interval(self):
        raise NotImplementedError('%s.interval not implemented' % type(self).__name__)


class FiveMinutesScheduler(RepeatingScheduler):
    def interval(self):
        return 5 * 60
