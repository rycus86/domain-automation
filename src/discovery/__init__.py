import abc
import logging

from metrics import Gauge


logger = logging.getLogger('docker-discovery')

subdomain_counter = Gauge(
    'domain_automation_discovery_subdomains',
    'Number of subdomains managed'
)


class Discovery(object):
    def iter_subdomains(self):
        collected = set()

        for subdomain in self._iter_subdomains():
            if subdomain.full in collected:
                continue

            collected.add(subdomain.full)

            logger.info('Processing %s ...' % subdomain.full)

            yield subdomain

        subdomain_counter.set(len(collected))

    @abc.abstractmethod
    def _iter_subdomains(self):
        raise NotImplementedError('%s.iter_subdomains not implemented' % type(self).__name__)

