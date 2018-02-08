import unittest

from discovery.docker_labels import DockerLabelsDiscovery


class MockService(object):
    def __init__(self, as_dict=None, **labels):
        if labels:
            self.labels = dict(labels)
        elif as_dict:
            self.labels = as_dict
        else:
            self.labels = dict()

    @property
    def attrs(self):
        return {
            'Spec': {
                'Labels': dict(self.labels)
            }
        }


class MockDockerClient(object):
    def __init__(self):
        self.items = list()

    @property
    def services(self):
        return self

    def list(self):
        return self.items


class DockerDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.client = MockDockerClient()
        self.discovery = DockerLabelsDiscovery()
        self.discovery.client = self.client

    def test_simple_subdomain_name(self):
        self.discovery.default_domain = 'test.net'

        self.client.items.append(
            MockService({'discovery.domain.name': 'sample'})
        )

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, 'sample')
        self.assertEqual(subdomains[0].base, 'test.net')
        self.assertEqual(subdomains[0].full, 'sample.test.net')

    def test_full_domain_name(self):
        self.discovery.default_domain = 'domain.com'

        self.client.items.append(
            MockService({'discovery.domain.name': 'sample.domain.com'})
        )

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, 'sample')
        self.assertEqual(subdomains[0].base, 'domain.com')
        self.assertEqual(subdomains[0].full, 'sample.domain.com')

    def test_sub_subdomain(self):
        self.discovery.default_domain = 'example.io'

        self.client.items.extend([
            MockService({'discovery.domain.name': 'abc.def'}),
            MockService({'discovery.domain.name': 'zzz.xyz.example.io'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 2)
        self.assertEqual(subdomains[0].name, 'abc.def')
        self.assertEqual(subdomains[0].base, 'example.io')
        self.assertEqual(subdomains[0].full, 'abc.def.example.io')
        self.assertEqual(subdomains[1].name, 'zzz.xyz')
        self.assertEqual(subdomains[1].base, 'example.io')
        self.assertEqual(subdomains[1].full, 'zzz.xyz.example.io')

    def test_no_subdomain(self):
        self.discovery.default_domain = 'short.co.uk'

        self.client.items.append(
            MockService({'discovery.domain.name': 'short.co.uk'})
        )

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, '')
        self.assertEqual(subdomains[0].base, 'short.co.uk')
        self.assertEqual(subdomains[0].full, 'short.co.uk')

    def test_duplicates(self):
        self.discovery.default_domain = 'duplicat.es'

        self.client.items.extend([
            MockService({'discovery.domain.name': 'www'}),
            MockService({'discovery.domain.name': 'test'}),
            MockService({'discovery.domain.name': 'www.duplicat.es'}),
            MockService({'discovery.domain.name': 'demo.duplicat.es'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 3)
        self.assertEqual(subdomains[0].name, 'www')
        self.assertEqual(subdomains[0].base, 'duplicat.es')
        self.assertEqual(subdomains[0].full, 'www.duplicat.es')
        self.assertEqual(subdomains[1].name, 'test')
        self.assertEqual(subdomains[1].base, 'duplicat.es')
        self.assertEqual(subdomains[1].full, 'test.duplicat.es')
        self.assertEqual(subdomains[2].name, 'demo')
        self.assertEqual(subdomains[2].base, 'duplicat.es')
        self.assertEqual(subdomains[2].full, 'demo.duplicat.es')
