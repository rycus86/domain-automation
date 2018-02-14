import signal
import logging

import factories


logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')
logger = logging.getLogger('domain-automation')
logger.setLevel(logging.INFO)


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


def setup_signals(scheduler, notifications):
    def exit_app():
        scheduler.cancel()
        notifications.message('Application exiting')

    signal.signal(signal.SIGINT, lambda *x: exit_app())
    signal.signal(signal.SIGTERM, lambda *x: exit_app())


def main():
    scheduler = factories.get_scheduler()
    notifications = factories.get_notification_manager()

    setup_signals(scheduler, notifications)

    schedule(scheduler, notifications)


if __name__ == '__main__':
    main()
