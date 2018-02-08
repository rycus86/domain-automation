import abc


class DNSManager(object):
    @abc.abstractmethod
    def get_current_public_ip(self):
        raise NotImplementedError('%s.get_current_public_ip not implemented' % type(self).__name__)

    @abc.abstractmethod
    def get_current_ip(self, subdomain):
        raise NotImplementedError('%s.get_current_ip not implemented' % type(self).__name__)

    def needs_update(self, subdomain, public_ip):
        return public_ip != self.get_current_ip(subdomain)

    @abc.abstractmethod
    def update(self, subdomain, public_ip):
        raise NotImplementedError('%s.update not implemented' % type(self).__name__)

