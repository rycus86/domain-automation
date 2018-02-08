import abc


class Scheduler(object):
    @abc.abstractmethod
    def schedule(self, func, *args, **kwargs):
        raise NotImplementedError('%s.schedule not implemented' % type(self).__name__)

