import abc


class Discovery(object):
    @abc.abstractmethod
    def iter_subdomains(self):
        raise NotImplementedError('%s.iter_subdomains not implemented' % type(self).__name__)

