from notifications import NotificationManager


class NoopNotificationManager(NotificationManager):
    def dns_updated(self, subdomain, result):
        pass

    def ssl_updated(self, subdomain, result):
        pass

    def message(self, text):
        pass
