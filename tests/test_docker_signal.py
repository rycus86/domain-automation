import logging
import unittest

from config import Subdomain
from notifications import docker_signal


class MockContainer(object):
    def __init__(self, id, name, labels=None, attrs=None):
        self.id = id
        self.name = name
        self.labels = labels or dict()
        self.image = None
        self.log_driver = 'json-file'
        self.log_config = dict()
        self.killed_with = None

    def kill(self, signal):
        self.killed_with = signal

    @property
    def attrs(self):
        return {
            'Config': {
                'Image': self.image
            },
            'HostConfig': {
                'LogConfig': {
                    'Type': self.log_driver,
                    'Config': self.log_config
                }
            }
        }


class MockService(dict):
    def __getattr__(self, name):
        return self[name]
    
    def tasks(self):
        return self._tasks

    def remove(self):
        self['removed'] = True

    def logs(self, **kwargs):
        for line in self._logs:
            yield line


class MockDockerServices(object):
    def __init__(self, client, tasks):
        self._client = client
        self._tasks = tasks

    def create(self, image, **kwargs):
        service = MockService(
            image=image,
            _tasks=self._tasks,
            _logs=self._client.service_logs,
            removed=False,
            **kwargs
        )

        self._client.service = service

        return service


class MockDockerClient(object):
    def __init__(self):
        self.items = list()
        self.tasks = list()
        self.swarm_mode = True
        self.service = None
        self.service_logs = ['output-1\n', 'output-2\n']

    @property
    def containers(self):
        return self

    def get(self, id):
        for item in self.items:
            if item.id == id:
                return item

    def list(self, filters):
        return list(self.items)

    @property
    def swarm(self):
        _self = self

        class MockSwarm(object):
            @property
            def attrs(self):
                return {'swarm': True} if _self.swarm_mode else {}

        return MockSwarm()

    @property
    def services(self):
        return MockDockerServices(self, self.tasks)


class MockLogContext(object):
    def __init__(self, name):
        self.name = name
        self.output = list()

        self.original_logger_debug = docker_signal.logger.debug
        self.original_logger_info = docker_signal.logger.info
        self.original_logger_error = docker_signal.logger.error

    def __enter__(self):
        def log(level, message):
            self.output.append('%s:%s:%s' % (level, self.name, message))

        docker_signal.logger.debug = lambda m: log('DEBUG', m)
        docker_signal.logger.info = lambda m: log('INFO', m)
        docker_signal.logger.error = lambda m: log('ERROR', m)
        
        return self

    def __exit__(self, *args, **kwargs):
        docker_signal.logger.debug = self.original_logger_debug
        docker_signal.logger.info = self.original_logger_info
        docker_signal.logger.error = self.original_logger_error


class DockerSignalNotificationTest(unittest.TestCase):
    def setUp(self):
        self.original_sleep = docker_signal.time.sleep
        self.manager = docker_signal.DockerSignalNotification()
        self.client = MockDockerClient()
        self.manager.client = self.client
        self.manager.label_name = 'test.label'

        if not hasattr(self, 'assertLogs'):
            setattr(self, 'assertLogs', self._assert_logs)

    def tearDown(self):
        docker_signal.time.sleep = self.original_sleep

    def _assert_logs(self, name, level):
        return MockLogContext(name)

    def test_external_main(self):
        self.client.items.extend([
            MockContainer('c1', 'container-hup', {'external.test': 'HUP'}),
            MockContainer('c2', 'container-int', {'external.test': 'INT'}),
            MockContainer('c3', 'container-none', {'different.label': 'x'})
        ])

        docker_signal.main(self.client, ['--label', 'external.test'])

        self.assertEqual(self.client.items[0].killed_with, 'HUP')
        self.assertEqual(self.client.items[1].killed_with, 'INT')
        self.assertIsNone(self.client.items[2].killed_with)

    def test_update_non_swarm(self):
        self.client.swarm_mode = False
        self.client.items.extend([
            MockContainer('c1', 'container-term', {'test.label': 'TERM'}),
            MockContainer('c2', 'container-kill', {'test.label': 'KILL'})
        ])

        self.manager.ssl_updated(Subdomain('test'), 'OK')

        self.assertEqual(self.client.items[0].killed_with, 'TERM')
        self.assertEqual(self.client.items[1].killed_with, 'KILL')

    def test_update_swarm_mode(self):
        self.client.swarm_mode = True

        container = MockContainer(
            'c-self', 'test-automation-container'
        )
        container.image = 'domain/automation'
        container.log_driver = 'custom'
        container.log_config = {'x-opt': 'abcd'}

        self.client.items.append(container)
        self.client.tasks.append({
            'DesiredState': 'running',
            'Status': {
                'State': 'running'
            }
        })

        docker_signal.get_current_container_id = lambda: 'c-self'

        def mock_sleep(seconds):
            # change the task state instead
            self.client.tasks[0]['DesiredState'] = 'shutdown'
            self.client.tasks[0]['Status']['State'] = 'complete'

        docker_signal.time.sleep = mock_sleep
        
        self.manager.label_name = 'test.label'

        with self.assertLogs('docker-signal', level='INFO') as logs:
            self.manager.ssl_updated(Subdomain('swarm'), 'OK')

        self.assertIsNotNone(self.client.service)
        self.assertEqual(self.client.service.image, 'domain/automation')
        self.assertEqual(self.client.service.command[-2:], ['--label', 'test.label'])
        self.assertIn('domain-automation-', self.client.service.name)
        self.assertGreater(len(self.client.service.env), 0)
        self.assertIn('PYTHONPATH=', self.client.service.env[0])
        self.assertEqual(self.client.service.log_driver, 'custom')
        self.assertEqual(self.client.service.log_driver_options, {'x-opt': 'abcd'})
        self.assertEqual(self.client.service.mode.mode, 'global')
        self.assertEqual(self.client.service.restart_policy['Condition'], 'none')
        self.assertEqual(self.client.service.restart_policy['MaxAttempts'], 0)
        self.assertTrue(self.client.service.removed)

        self.assertEqual(len(logs.output), 2)
        self.assertEqual(
            logs.output[0], 
            'INFO:docker-signal:Signalled containers with label %s - result: %s' %
            ('test.label', 'complete')
        )
        self.assertEqual(
            logs.output[1],
            'INFO:docker-signal:Signal logs: %s' %
            'output-1\noutput-2'
        )
        
    def test_failing_swarm_mode(self):
        self.client.swarm_mode = True
        self.manager.label_name = 'test.failing'

        self.manager.ssl_updated(Subdomain('swarm'), 'Failed')
        self.assertIsNone(self.client.service)

        docker_signal.get_current_container_id = lambda: None

        self.manager.ssl_updated(Subdomain('swarm'), 'OK')
        self.assertIsNone(self.client.service)

        docker_signal.get_current_container_id = lambda: 'c-self'

        self.manager.ssl_updated(Subdomain('swarm'), 'OK')
        self.assertIsNone(self.client.service)

        self.client.items.append(
            MockContainer('c-self', 'own-container')
        )

        self.manager.ssl_updated(Subdomain('swarm'), 'OK')
        self.assertIsNone(self.client.service)

        self.client.items[0].image = 'test/image'
        self.client.tasks.append({
            'DesiredState': 'shutdown',
            'Status': {
                'State': 'failed'
            }
        })

        self.client.service_logs[:] = ['failed to send signal']
 
        with self.assertLogs('docker-signal', level='INFO') as logs:
            self.manager.ssl_updated(Subdomain('swarm'), 'OK')

        self.assertEqual(len(logs.output), 2)
        self.assertEqual(
            logs.output[0], 
            'INFO:docker-signal:Signalled containers with label %s - result: %s' %
            ('test.failing', 'failed')
        )
        self.assertEqual(
            logs.output[1],
            'INFO:docker-signal:Signal logs: %s' %
            'failed to send signal'
        )

        self.assertIsNotNone(self.client.service)

