import docker_helper


base_domain = 'localhost.local'
default_config_path = '/var/secrets/app.config'


def read_configuration(key, path, default=None):
    value = docker_helper.read_configuration(key, path)

    if value or path == default_config_path:
        return value or default

    return docker_helper.read_configuration(
        key, default_config_path, default=default
    )


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

    def __str__(self):
        return self.full
