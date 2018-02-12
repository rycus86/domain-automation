import docker

from docker_helper import read_configuration

from config import Subdomain, base_domain
from discovery import Discovery


class DockerLabelsDiscovery(Discovery):
    def __init__(self):
        self.client = docker.from_env()
        self.label_name = read_configuration(
            'DOCKER_DISCOVERY_LABEL', '/var/secrets/discovery', 'discovery.domain.name'
        )
        self.default_domain = read_configuration(
            'DEFAULT_DOMAIN', '/var/secrets/app.config', base_domain
        )

    def _iter_subdomains(self):
        if len(self.client.swarm.attrs) > 0:
            for service in self.client.services.list():
                labels = service.attrs['Spec'].get('Labels', dict())

                for subdomain in self._iter_labels(labels):
                    yield subdomain

        for container in self.client.containers.list():
            for subdomain in self._iter_labels(container.labels):
                yield subdomain

    def _iter_labels(self, labels):
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
