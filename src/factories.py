from config import read_configuration, default_config_path


scheduler_class = read_configuration(
    'SCHEDULER_CLASS', default_config_path, 'scheduler.oneshot.OneShotScheduler'
)
discovery_class = read_configuration(
    'DISCOVERY_CLASS', default_config_path, 'discovery.noop.NoopDiscovery'
)
dns_manager_class = read_configuration(
    'DNS_MANAGER_CLASS', default_config_path, 'dns_manager.noop.NoopDNSManager'
)
ssl_manager_class = read_configuration(
    'SSL_MANAGER_CLASS', default_config_path, 'ssl_manager.noop.NoopSSLManager'
)
notification_manager_class = read_configuration(
    'NOTIFICATION_MANAGER_CLASS', default_config_path,
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
