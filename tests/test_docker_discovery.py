import unittest

from discovery.docker_labels import DockerLabelsDiscovery


class MockService(object):
    def __init__(self, as_dict=None, **labels):
        if labels:
            self._labels = dict(labels)
        elif as_dict:
            self._labels = as_dict
        else:
            self._labels = dict()

    @property
    def attrs(self):
        return {
            'Spec': {
                'Labels': dict(self._labels)
            }
        }


class MockContainer(object):
    def __init__(self, as_dict=None, **labels):
        if labels:
            self._labels = dict(labels)
        elif as_dict:
            self._labels = as_dict
        else:
            self._labels = dict()

    @property
    def labels(self):
        return dict(self._labels)


class MockDockerClient(object):
    def __init__(self, *items):
        self.items = list(items)
        self.services_list = list()
        self.containers_list = list()
        self.swarm_mode = True

    def add_all(self, items):
        for item in items:
            if isinstance(item, MockContainer):
                self.containers_list.append(item)
            else:
                self.services_list.append(item)

    @property
    def services(self):
        return MockDockerClient(*self.services_list)

    @property
    def containers(self):
        return MockDockerClient(*self.containers_list)

    def list(self):
        return self.items

    @property
    def swarm(self):
        _self = self

        class MockSwarm(object):
            @property
            def attrs(self):
                return {'swarm': True} if _self.swarm_mode else {}

        return MockSwarm()


class DockerDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.client = MockDockerClient()
        self.discovery = DockerLabelsDiscovery()
        self.discovery.client = self.client

    def test_simple_subdomain_name(self):
        self.discovery.default_domain = 'test.net'

        self.client.add_all([
            MockService({'discovery.domain.name': 'sample'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, 'sample')
        self.assertEqual(subdomains[0].base, 'test.net')
        self.assertEqual(subdomains[0].full, 'sample.test.net')

    def test_full_domain_name(self):
        self.discovery.default_domain = 'domain.com'

        self.client.add_all([
            MockService({'discovery.domain.name': 'sample.domain.com'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, 'sample')
        self.assertEqual(subdomains[0].base, 'domain.com')
        self.assertEqual(subdomains[0].full, 'sample.domain.com')

    def test_sub_subdomain(self):
        self.discovery.default_domain = 'example.io'

        self.client.add_all([
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

        self.client.add_all([
            MockService({'discovery.domain.name': 'short.co.uk'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, '')
        self.assertEqual(subdomains[0].base, 'short.co.uk')
        self.assertEqual(subdomains[0].full, 'short.co.uk')

    def test_duplicates(self):
        self.discovery.default_domain = 'duplicat.es'

        self.client.add_all([
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

    def test_services_and_containers(self):
        self.discovery.default_domain = 'mixed.targets'

        self.client.add_all([
            MockService({'discovery.domain.name': 'www'}),
            MockContainer({'discovery.domain.name': 'test'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 2)
        self.assertEqual(subdomains[0].name, 'www')
        self.assertEqual(subdomains[0].base, 'mixed.targets')
        self.assertEqual(subdomains[0].full, 'www.mixed.targets')
        self.assertEqual(subdomains[1].name, 'test')
        self.assertEqual(subdomains[1].base, 'mixed.targets')
        self.assertEqual(subdomains[1].full, 'test.mixed.targets')

    def test_not_in_swarm_mode(self):
        self.discovery.default_domain = 'non.swarm'

        self.client.swarm_mode = False
        self.client.add_all([
            MockService({'discovery.domain.name': 'www'}),
            MockContainer({'discovery.domain.name': 'test'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 1)
        self.assertEqual(subdomains[0].name, 'test')
        self.assertEqual(subdomains[0].base, 'non.swarm')
        self.assertEqual(subdomains[0].full, 'test.non.swarm')

    def test_multiple_label_names(self):
        self.discovery.label_names = 'first.label,additional.item'.split(',')
        self.discovery.default_domain = 'multi.labels'
        self.client.add_all([
            MockService({'first.label': 'first'}),
            MockService({'additional.item': 'second'})
        ])

        subdomains = list(self.discovery.iter_subdomains())

        self.assertEqual(len(subdomains), 2)
        self.assertEqual(subdomains[0].name, 'first')
        self.assertEqual(subdomains[0].full, 'first.multi.labels')
        self.assertEqual(subdomains[1].name, 'second')
        self.assertEqual(subdomains[1].full, 'second.multi.labels')
