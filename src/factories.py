import os


scheduler_class = os.environ.get('SCHEDULER_CLASS', 'scheduler.oneshot.OneShotScheduler')
discovery_class = os.environ.get('DISCOVERY_CLASS', 'discovery.noop.NoopDiscovery')
dns_manager_class = os.environ.get('DNS_MANAGER_CLASS', 'dns_manager.noop.NoopDNSManager')
ssl_manager_class = os.environ.get('SSL_MANAGER_CLASS', 'ssl_manager.noop.NoopSSLManager')
notification_manager_class = os.environ.get('NOTIFICATION_MANAGER_CLASS', 'notifications.noop.NoopNotificationManager')


def _instantiate(class_name):
    module_name, name = class_name.rsplit('.', 1)
    module = __import__(module_name)

    _, name = class_name.split('.', 1)

    parent = module
    while '.' in name:
        part, name = name.split('.', 1)
        parent = getattr(parent, part)

    clazz = getattr(parent, name)
    return clazz()


def get_scheduler():
    return _instantiate(scheduler_class)


def get_discovery():
    return _instantiate(discovery_class)


def get_dns_manager():
    return _instantiate(dns_manager_class)


def get_ssl_manager():
    return _instantiate(ssl_manager_class)


def get_notification_manager():
    return _instantiate(notification_manager_class)
