base_domain = 'localhost.local'


class Subdomain(object):
    def __init__(self, name, base=base_domain):
        self.name = name
        self.base = base

    @property
    def full(self):
        if self.name:
            return '%s.%s' % (self.name, self.base)

        else:
            return self.base
