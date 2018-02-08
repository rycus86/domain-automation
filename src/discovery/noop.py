from discovery import Discovery


class NoopDiscovery(Discovery):
    def iter_subdomains(self):
        return iter(list())
