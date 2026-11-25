"""Dwie wbudowane usługi HTTP. Nigdy nie przyjmują adresu celu od użytkownika."""
import http.client
import json
import random
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .db import SERVICES


class Laboratory:
    def __init__(self):
        self.lock = threading.Lock()
        self.faults = {}
        self.slots = {name: threading.BoundedSemaphore(2) for name in SERVICES}
        self.alive = False
        lab = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                name = self.path.removeprefix('/')
                if name not in SERVICES:
                    self.send_error(404)
                    return
                with lab.lock:
                    fault = lab.faults.get(name)
                if fault and time.monotonic() >= fault['expires']:
                    fault = None
                if fault and fault['kind'] == 'unavailability':
                    self.close_connection = True
                    return
                if fault and fault['kind'] == 'latency':
                    # Przerwanie opóźnienia przy stopie lub wygaśnięciu zakłócenia.
                    until = min(time.monotonic() + fault['intensity'] / 1000, fault['expires'])
                    while time.monotonic() < until:
                        with lab.lock:
                            if lab.faults.get(name) is not fault:
                                break
                        time.sleep(min(0.02, max(0, until-time.monotonic())))
                status = 200
                if fault and fault['kind'] == 'http_500' and random.randrange(100) < fault['intensity']:
                    status = 500
                acquired = lab.slots[name].acquire(blocking=False)
                if not acquired:
                    status = 503
                else:
                    try:
                        time.sleep(0.12)
                    finally:
                        lab.slots[name].release()
                data = json.dumps({'service': name, 'status': status}).encode()
                try:
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name='demo-http')

    def start(self):
        self.thread.start()
        self.alive = True

    def apply(self, service, kind, intensity, seconds):
        if service not in SERVICES or not self.alive:
            raise RuntimeError('Laboratorium nie jest dostępne.')
        with self.lock:
            self.faults[service] = dict(kind=kind, intensity=intensity, expires=time.monotonic()+seconds)

    def clear(self, service):
        with self.lock:
            self.faults.pop(service, None)

    def request(self, service):
        if service not in SERVICES:
            raise ValueError('Cel spoza laboratorium.')
        start = time.monotonic()
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        status, error = None, None
        try:
            conn.request('GET', '/' + service)
            reply = conn.getresponse()
            reply.read()
            status = reply.status
        except (TimeoutError, socket.timeout):
            error = 'timeout'
        except (OSError, http.client.HTTPException):
            error = 'connection'
        finally:
            conn.close()
        return dict(status=status, error=error, elapsed_ms=(time.monotonic()-start)*1000)

    def close(self):
        self.alive = False
        with self.lock:
            self.faults.clear()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
