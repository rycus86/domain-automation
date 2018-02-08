import os


scheduler_class = os.environ.get('SCHEDULER_CLASS', 'scheduler.noop.NoopScheduler')


def _instantiate(class_name):
    pass


def get_scheduler():
    return _instantiate(scheduler_class)


def get_discovery():
    pass


def get_dns_manager():
    pass


def get_ssl_manager():
    pass


def get_notification_manager():
    pass

