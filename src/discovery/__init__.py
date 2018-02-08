import abc


class Discovery(object):
    def iter_subdomains(self):
        seen = set()

        for subdomain in self._iter_subdomains():
            if subdomain.full in seen:
                continue

            seen.add(subdomain.full)

            yield subdomain

    @abc.abstractmethod
    def _iter_subdomains(self):
        raise NotImplementedError('%s.iter_subdomains not implemented' % type(self).__name__)

