import os
import docker

from config import Subdomain, base_domain
from discovery import Discovery


class DockerLabelsDiscovery(Discovery):
    def __init__(self):
        self.client = docker.from_env()
        self.label_name = os.environ.get('DOCKER_DISCOVERY_LABEL', 'discovery.domain.name')
        self.default_domain = os.environ.get('DEFAULT_DOMAIN', base_domain)

    def _iter_subdomains(self):
        for service in self.client.services.list():
            labels = service.attrs['Spec'].get('Labels', dict())

            for name, value in labels.items():
                if name == self.label_name:
                    for domain_name in value.split(','):
                        yield self._to_subdomain(domain_name.strip())

    def _to_subdomain(self, name):
        if name == self.default_domain:
            return Subdomain('', self.default_domain)

        elif name.endswith(self.default_domain):
            return Subdomain(name.replace('.%s' % self.default_domain, ''), self.default_domain)

        else:
            return Subdomain(name, self.default_domain)
