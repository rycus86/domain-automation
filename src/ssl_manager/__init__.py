import abc


class SSLManager(object):
    RESULT_NOT_YET_DUE_FOR_RENEWAL = 'Not yet due for renewal'

    @abc.abstractmethod
    def needs_update(self, subdomain):
        raise NotImplementedError('%s.needs_update not implemented' % type(self).__name__)

    @abc.abstractmethod
    def update(self, subdomain):
        raise NotImplementedError('%s.update not implemented' % type(self).__name__)

