import logging
import requests
import CloudFlare

from config import read_configuration
from metrics import Counter
from dns_manager import DNSManager


logger = logging.getLogger('dns-cloudflare')

dns_records_created = Counter(
    'domain_automation_dns_cloudflare_created',
    'Number of DNS records created in total'
)
dns_records_updated = Counter(
    'domain_automation_dns_cloudflare_updated',
    'Number of DNS records updated in total'
)
dns_records_failed = Counter(
    'domain_automation_dns_cloudflare_failed',
    'Number of DNS records failed to create or update'
)


class CloudflareDNSManager(DNSManager):
    def __init__(self):
        self.cloudflare = CloudFlare.CloudFlare(
            email=read_configuration('CLOUDFLARE_EMAIL', '/var/secrets/cloudflare'),
            token=read_configuration('CLOUDFLARE_TOKEN', '/var/secrets/cloudflare')
        )

        self._zones = dict()
        self._dns_records = dict()

    def get_current_public_ip(self):
        try:
            response = requests.get('https://api.ipify.org')

            if response.status_code // 100 == 2:
                return response.text.strip()

        except Exception as ex:
            logger.error('Failed to find the Public IP address', exc_info=ex)

    def _get_zone(self, subdomain):
        try:
            if not self._zones:
                self._zones = {
                    zone['name']: zone for zone in self.cloudflare.zones.get()
                }

            return self._zones.get(subdomain.base)

        except Exception as ex:
            logger.error('Failed to find the zone for %s' % subdomain.base, exc_info=ex)

    def _get_dns_record(self, subdomain):
        try:
            zone = self._get_zone(subdomain)

            if zone:
                zone_id = zone['id']

                if zone_id not in self._dns_records:
                    self._dns_records[zone_id] = {
                        record['name']: record
                        for record in self.cloudflare.zones.dns_records.get(zone_id)
                        if record['type'] == 'A'
                    }

                return self._dns_records.get(zone_id, dict()).get(subdomain.full)

        except Exception as ex:
            logger.error('Failed to find the DNS records for %s' % subdomain.base, exc_info=ex)

    def get_current_ip(self, subdomain):
        record = self._get_dns_record(subdomain)

        if record:
            return record.get('content')

    def _update_dns_record(self, subdomain, public_ip, record):
        try:
            self._dns_records.clear()

            record = self.cloudflare.zones.dns_records.put(
                record['zone_id'], record['id'],
                data=dict(
                    name=subdomain.name, type='A',
                    content=public_ip, proxied=record.get('proxied', True)
                )
            )

            if record and record['content'] == public_ip and record['name'] == subdomain.full:
                dns_records_updated.inc()

                return 'OK, updated [%s]' % public_ip

        except Exception as ex:
            logger.error('Failed to update the DNS records for %s' % subdomain.full, exc_info=ex)

        dns_records_failed.inc()

        return 'Failed to update'

    def _create_dns_record(self, subdomain, public_ip, zone):
        try:
            self._dns_records.clear()

            record = self.cloudflare.zones.dns_records.post(
                zone['id'], data=dict(name=subdomain.name, type='A', content=public_ip, proxied=True)
            )

            if record and record['content'] == public_ip and record['name'] == subdomain.full:
                dns_records_created.inc()

                return 'OK, created [%s]' % public_ip

        except Exception as ex:
            logger.error('Failed to create the DNS records for %s' % subdomain.full, exc_info=ex)

        dns_records_failed.inc()

        return 'Failed to create'

    def update(self, subdomain, public_ip):
        if not public_ip:
            logger.error('Public IP is not available')
            return 'Failed'

        record = self._get_dns_record(subdomain)

        if record:
            return self._update_dns_record(subdomain, public_ip, record)

        else:
            zone = self._get_zone(subdomain)

            if not zone:
                return 'Failed to find zone'

            return self._create_dns_record(subdomain, public_ip, zone)
