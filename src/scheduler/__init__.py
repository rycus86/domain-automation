import abc


class Scheduler(object):
    @abc.abstractmethod
    def schedule(self, func, *args, **kwargs):
        raise NotImplementedError('%s.schedule not implemented' % type(self).__name__)

    @abc.abstractmethod
    def run_now(self):
        raise NotImplementedError('%s.run_now not implemented' % type(self).__name__)

    @abc.abstractmethod
    def cancel(self):
        raise NotImplementedError('%s.cancel not implemented' % type(self).__name__)
