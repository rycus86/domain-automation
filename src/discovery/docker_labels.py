import docker

from config import Subdomain, base_domain, read_configuration, default_config_path
from discovery import Discovery


class DockerLabelsDiscovery(Discovery):
    def __init__(self):
        self.client = docker.from_env()
        self.label_names = read_configuration(
            'DOCKER_DISCOVERY_LABEL', '/var/secrets/discovery', 'discovery.domain.name'
        ).split(',')
        self.default_domain = read_configuration(
            'DEFAULT_DOMAIN', default_config_path, base_domain
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
            if name in self.label_names:
                for domain_name in value.split(','):
                    yield self._to_subdomain(domain_name.strip())

    def _to_subdomain(self, name):
        if name == self.default_domain:
            return Subdomain('', self.default_domain)

        elif name.endswith(self.default_domain):
            return Subdomain(name.replace('.%s' % self.default_domain, ''), self.default_domain)

        else:
            return Subdomain(name, self.default_domain)
