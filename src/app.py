import os
import signal
import logging

from datetime import datetime

import factories

from config import read_configuration, default_config_path
from metrics import MetricsServer


logging.basicConfig(format='%(asctime)s (%(name)s) %(funcName)s [%(levelname)s] %(message)s')
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger('app-main')


def check(subdomain, public_ip, dns, ssl, notifications):
    if dns.needs_update(subdomain, public_ip):
        try:
            dns_result = dns.update(subdomain, public_ip)

        except Exception as ex:
            dns_result = 'Failed: %s' % ex

        notifications.dns_updated(subdomain, dns_result)

    else:
        logger.info('No DNS update needed for %s' % subdomain)
    
    if ssl.needs_update(subdomain):
        try:
            ssl_result = ssl.update(subdomain)

        except Exception as ex:
            ssl_result = 'Failed: %s' % ex
            
        notifications.ssl_updated(subdomain, ssl_result)

    else:
        logger.info('No SSL update needed for %s' % subdomain)


def check_all(discovery, dns, ssl, notifications):
    public_ip = dns.get_current_public_ip()

    logger.info('Starting checks with public IP: %s' % public_ip)

    for subdomain in discovery.iter_subdomains():
        check(subdomain, public_ip, dns, ssl, notifications)


def schedule(scheduler, notifications):
    discovery = factories.get_discovery()
    dns = factories.get_dns_manager()
    ssl = factories.get_ssl_manager()

    app_version = os.environ.get('GIT_COMMIT') or 'unknown'
    app_build_time = str(datetime.fromtimestamp(
        float(os.environ.get('BUILD_TIMESTAMP') or '0')
    ))

    notifications.message(
        'Application starting (version: %s, built: %s)' %
        (app_version, app_build_time)
    )

    scheduler.schedule(check_all, discovery, dns, ssl, notifications)


def setup_signals(scheduler, notifications, metrics_server):
    def exit_app():
        notifications.message('Application exiting')
        scheduler.cancel()

        if metrics_server:
            metrics_server.stop()

    signal.signal(signal.SIGINT, lambda *x: exit_app())
    signal.signal(signal.SIGTERM, lambda *x: exit_app())

    signal.signal(signal.SIGHUP, lambda *x: scheduler.run_now())


def setup_metrics():
    metrics_port = read_configuration('METRICS_PORT', default_config_path)

    if metrics_port:
        metrics_host = read_configuration(
            'METRICS_HOST', default_config_path, '0.0.0.0'
        )

        server = MetricsServer(port=int(metrics_port), host=metrics_host)
        server.start()

        return server


def main():
    scheduler = factories.get_scheduler()
    notifications = factories.get_notification_manager()
    metrics_server = setup_metrics()

    setup_signals(scheduler, notifications, metrics_server)

    schedule(scheduler, notifications)


if __name__ == '__main__':
    main()
