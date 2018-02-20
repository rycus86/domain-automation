import signal
import logging

import factories

from config import read_configuration, default_config_path


logging.basicConfig(format='%(asctime)s (%(name)s) %(module)s.%(funcName)s\n[%(levelname)s] %(message)s')
logging.getLogger().setLevel(logging.INFO)


def check(subdomain, public_ip, dns, ssl, notifications):
    if dns.needs_update(subdomain, public_ip):
        try:
            dns_result = dns.update(subdomain, public_ip)

        except Exception as ex:
            dns_result = 'Failed: %s' % ex

        notifications.dns_updated(subdomain, dns_result)
    
    if ssl.needs_update(subdomain):
        try:
            ssl_result = ssl.update(subdomain)

        except Exception as ex:
            ssl_result = 'Failed: %s' % ex
            
        notifications.ssl_updated(subdomain, ssl_result)


def check_all(discovery, dns, ssl, notifications):
    public_ip = dns.get_current_public_ip()

    for subdomain in discovery.iter_subdomains():
        check(subdomain, public_ip, dns, ssl, notifications)


def schedule(scheduler, notifications):
    discovery = factories.get_discovery()
    dns = factories.get_dns_manager()
    ssl = factories.get_ssl_manager()

    notifications.message('Application starting')

    scheduler.schedule(check_all, discovery, dns, ssl, notifications)


def setup_signals(scheduler, notifications, metrics_server):
    def exit_app():
        notifications.message('Application exiting')
        scheduler.cancel()

        if metrics_server:
            metrics_server.stop()

    signal.signal(signal.SIGINT, lambda *x: exit_app())
    signal.signal(signal.SIGTERM, lambda *x: exit_app())


def setup_metrics():
    metrics_port = read_configuration('METRICS_PORT', default_config_path)

    if metrics_port:
        metrics_host = read_configuration(
            'METRICS_HOST', default_config_path, '0.0.0.0'
        )

        from metrics import MetricsServer

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
