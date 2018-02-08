import abc


class SSLManager(object):
    @abc.abstractmethod
    def needs_update(subdomain):
        raise NotImplementedError('%s.needs_update not implemented' % type(self).__name__)

    @abc.abstractmethod
    def update(subdomain): 
        raise NotImplementedError('%s.update not implemented' % type(self).__name__)

