import unittest

from config import Subdomain
from dns_manager import cloudflare_dns as cf_dns


class MockRequests(object):
    status = 200
    ip_address = '1.1.1.1'

    def get(self, *args):
        class MockResponse(object):
            @property
            def status_code(self):
                return MockRequests.status

            @property
            def text(self):
                return MockRequests.ip_address

        return MockResponse()


class MockDnsRecords(object):
    def __init__(self):
        self.base = 'none'
        self.records = dict()

    def get(self, zone_id):
        return self.records.get(zone_id, list())

    def post(self, zone_id, data):
        record = {
            'id': 'r-%s-%s' % (zone_id, hash(str(data))),
            'zone_id': zone_id,
            'name': '%s.%s' % (data['name'], self.base),
            'type': data['type'],
            'content': data['content']
        }

        if zone_id not in self.records:
            self.records[zone_id] = list()

        self.records[zone_id].append(record)

        return record

    def put(self, zone_id, record_id, data):
        record = next(rec for rec in self.records[zone_id] if rec['id'] == record_id)
        record['name'] = '%s.%s' % (data['name'], self.base)
        record['content'] = data['content']
        record['type'] = data['type']
        return record


class MockZones(object):
    def __init__(self):
        self.items = list()
        self.dns_records = MockDnsRecords()

    def get(self):
        return self.items


class MockCloudFlare(object):
    def __init__(self):
        self.zones = MockZones()


class CloudflareDNSTest(unittest.TestCase):
    def setUp(self):
        self.manager = cf_dns.CloudflareDNSManager()
        cf_dns.requests = MockRequests()

        self.cf = MockCloudFlare()
        self.manager.cloudflare = self.cf

    def test_public_ip(self):
        MockRequests.ip_address = '5.6.7.8'

        address = self.manager.get_current_public_ip()

        self.assertIsNotNone(address)
        self.assertEqual(address, '5.6.7.8')

    def test_current_ip(self):
        self.cf.zones.items.append({
            'id': 'abcd1234', 'name': 'sample.com'
        })
        self.cf.zones.dns_records.records['abcd1234'] = [{
            'zone_id': 'abcd1234', 'type': 'A', 'name': 'test.sample.com', 'content': '9.9.9.9'
        }]

        address = self.manager.get_current_ip(Subdomain('test', 'sample.com'))

        self.assertIsNotNone(address)
        self.assertEqual(address, '9.9.9.9')

    def test_update(self):
        self.cf.zones.dns_records.base = 'sample.com'
        self.cf.zones.items.append({
            'id': 'abcd1234', 'name': 'sample.com'
        })

        result = self.manager.update(Subdomain('mock', 'sample.com'), '8.8.4.4')

        self.assertEqual('OK, created', result)

        result = self.manager.update(Subdomain('mock', 'sample.com'), '8.8.8.8')

        self.assertEqual('OK, updated', result)

