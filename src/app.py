import signal
import logging

import factories


logging.basicConfig(format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s')
logger = logging.getLogger('domain-automation')
logger.setLevel(logging.INFO)


def check(subdomain, public_ip, dns, ssl, notifications):
    if dns.needs_update(subdomain, public_ip):
        dns_result = dns.update(subdomain, public_ip)
        notifications.dns_updated(subdomain, dns_result)
    
    if ssl.needs_update(subdomain):
        ssl_result = ssl.update(subdomain)
        notifications.ssl_updated(subdomain, ssl_result)


def check_all(discovery, dns, ssl, notifications):
    public_ip = dns.get_current_public_ip()

    for subdomain in discovery.iter_subdomains():
        check(subdomain, public_ip, dns, ssl, notifications)


def schedule(scheduler):
    discovery = factories.get_discovery()
    dns = factories.get_dns_manager()
    ssl = factories.get_ssl_manager()
    notifications = factories.get_notification_manager()

    scheduler.schedule(check_all, discovery, dns, ssl, notifications)


def setup_signals(scheduler):
    signal.signal(signal.SIGINT, lambda *x: scheduler.cancel())
    signal.signal(signal.SIGTERM, lambda *x: scheduler.cancel())


def main():
    scheduler = factories.get_scheduler()

    setup_signals(scheduler)

    schedule(scheduler)


if __name__ == '__main__':
    main()
