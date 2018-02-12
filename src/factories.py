from docker_helper import read_configuration


scheduler_class = read_configuration(
    'SCHEDULER_CLASS', '/var/secrets/app.config', 'scheduler.oneshot.OneShotScheduler'
)
discovery_class = read_configuration(
    'DISCOVERY_CLASS', '/var/secrets/app.config', 'discovery.noop.NoopDiscovery'
)
dns_manager_class = read_configuration(
    'DNS_MANAGER_CLASS', '/var/secrets/app.config', 'dns_manager.noop.NoopDNSManager'
)
ssl_manager_class = read_configuration(
    'SSL_MANAGER_CLASS', '/var/secrets/app.config', 'ssl_manager.noop.NoopSSLManager'
)
notification_manager_class = read_configuration(
    'NOTIFICATION_MANAGER_CLASS', '/var/secrets/app.config', 
    'notifications.noop.NoopNotificationManager'
)


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
    if ',' in notification_manager_class:
        managers = [
            _instantiate(nm.strip() for nm in notification_manager_class.split(','))
        ]

        return NotificationManager(*managers)

    else:
        return _instantiate(notification_manager_class)
