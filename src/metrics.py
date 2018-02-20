import os
import threading

try:
    from http.server import HTTPServer
    from socketserver import ThreadingMixIn
except ImportError:
    from BaseHTTPServer import HTTPServer
    from SocketServer import ThreadingMixIn

from prometheus_client import MetricsHandler
from prometheus_client import Histogram, Summary, Counter, Gauge


# metrics
app_info = Gauge(
    'domain_automation_app_info', 'Application info',
    labelnames=('version',)
)
app_info.labels(
    os.environ.get('GIT_COMMIT') or 'unknown'
).set(1)

app_built_at = Gauge(
    'domain_automation_app_built_at', 'Application build timestamp'
)
app_built_at.set(float(os.environ.get('BUILD_TIMESTAMP') or '0'))


class _HttpServer(ThreadingMixIn, HTTPServer):
    pass


class MetricsServer(object):
    def __init__(self, port, host='0.0.0.0'):
        self.port = port
        self.host = host

        self._httpd = None

    def start(self):
        self._httpd = _HttpServer((self.host, self.port), MetricsHandler)

        thread = threading.Thread(target=self._run)
        thread.setDaemon(True)
        thread.start()

    def _run(self):
        self._httpd.serve_forever()

    def stop(self):
        self._httpd.shutdown()
