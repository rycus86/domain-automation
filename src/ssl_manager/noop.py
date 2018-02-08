from ssl_manager import SSLManager


class NoopSSLManager(SSLManager):
    def needs_update(self, subdomain):
        return False

    def update(self, subdomain):
        pass
