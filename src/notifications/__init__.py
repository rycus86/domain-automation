import logging


logger = logging.getLogger('notifications')


def _ignore_errors():
    class IgnoreErrorsContext(object):
        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_val:
                logger.error('Exception during a notification', exc_info=exc_val)

            return True

    return IgnoreErrorsContext()


class NotificationManager(object):
    def __init__(self, *delegates):
        self.delegates = delegates

    def dns_updated(self, subdomain, result):
        for delegate in self.delegates:
            with _ignore_errors():
                delegate.dns_updated(subdomain, result)
    
    def ssl_updated(self, subdomain, result):
        for delegate in self.delegates:
            with _ignore_errors():
                delegate.ssl_updated(subdomain, result)

    def message(self, text):
        for delegate in self.delegates:
            with _ignore_errors():
                delegate.message(text)
