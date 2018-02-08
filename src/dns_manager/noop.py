from dns_manager import DNSManager


class NoopDNSManager(DNSManager):
    def get_current_public_ip(self):
        return None

    def get_current_ip(self, subdomain):
        return None

    def needs_update(self, subdomain, public_ip):
        return False

    def update(self, subdomain, public_ip):
        pass
