class NotificationManager(object):
    def __init__(self, *delegates):
        self.delegates = delegates

    def dns_updated(self, subdomain, result):
        for delegate in self.delegates:
            delegate.dns_updated(subdomain, result)
    
    def ssl_updated(self, subdomain, result):
        for delegate in self.delegates:
            delegate.ssl_updated(subdomain, result)

    def message(self, text):
        for delegate in self.delegates:
            delegate.message(text)

