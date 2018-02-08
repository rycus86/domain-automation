from scheduler import Scheduler


class OneShotScheduler(Scheduler):
    def schedule(self, func, *args, **kwargs):
        func(*args, **kwargs)
