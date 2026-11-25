import json
import http.cookiejar
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from app import ProcessLock, create_app
from riskr.db import aggregate, connect, initialize
from riskr.engine import Engine, RuleError
from riskr.laboratory import Laboratory


class RiskRTests(unittest.TestCase):
    def setUp(self):
        workspace_tmp = Path(__file__).resolve().parents[1] / 'tmp'
        workspace_tmp.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=workspace_tmp)
        assert Path(self.temp.name).resolve().parent == workspace_tmp.resolve()
        self.path = Path(self.temp.name) / 'test.sqlite3'
        initialize(self.path)
        self.lab = Laboratory()
        self.lab.start()
        self.engine = Engine(self.path, self.lab, window=0.3, interval=0.1)
        self.app = create_app(self.path, self.engine)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.client.get('/health')
        with self.client.session_transaction() as session:
            self.token = session['csrf']

    def tearDown(self):
        self.engine.close()
        self.lab.close()
        self.temp.cleanup()

    def data(self, kind='http_500', intensity=100, duration=1, service='demo-api'):
        return dict(service_id=service, fault_type=kind, intensity=intensity, duration_seconds=duration)

    def wait(self, identifier):
        until = time.monotonic()+7
        while time.monotonic() < until:
            row = self.engine.get(identifier)
            if row['status'] not in ('starting','running','stopping'):
                return self.engine.snapshot(identifier)
            time.sleep(0.04)
        self.fail('Eksperyment nie zakończył się w limicie.')

    def post(self, path, data=None):
        return self.client.post(path, json=data, headers={'X-CSRF-Token': self.token})

    def test_views_and_draft_roundtrip(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/experiments/new').status_code, 200)
        saved = self.post('/api/experiments', self.data()).get_json()
        identifier = saved['id']
        self.assertIn(b'HTTP 500', self.client.get('/experiments/new?draft='+identifier).data)
        self.assertEqual(self.client.get('/experiments/'+identifier).status_code, 302)
        initialize(self.path)
        self.assertEqual(self.engine.get(identifier)['status'], 'draft')
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM service').fetchone()[0], 2)

    def test_server_validation_and_no_partial_writes(self):
        invalid = [self.data(duration=0), self.data(duration=301), self.data(intensity=101),
                   self.data(kind='unknown'), self.data(service='https://example.com'),
                   self.data(intensity=True), self.data(intensity=1.5), self.data(intensity=''),
                   self.data(kind='unavailability', intensity=50), self.data(kind='overload',intensity=51)]
        for value in invalid:
            with self.subTest(value=value):
                self.assertEqual(self.post('/api/experiments', value).status_code, 400)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM experiment').fetchone()[0], 0)

    def test_csrf_and_cross_origin(self):
        self.assertEqual(self.client.post('/api/experiments', json=self.data()).status_code, 403)
        self.assertEqual(self.client.post('/api/experiments', json=self.data(), headers={'X-CSRF-Token':self.token,'Origin':'https://example.com'}).status_code, 403)

    def test_unavailable_lab_blocks_start(self):
        row = self.engine.save(self.data())
        self.lab.alive = False
        with self.assertRaises(RuleError):
            self.engine.start(row['id'])
        self.assertEqual(self.engine.get(row['id'])['status'],'draft')

    def test_http500_is_scoped_and_automatically_removed(self):
        row = self.engine.save(self.data(duration=2))
        self.engine.start(row['id'])
        self.assertEqual(self.lab.request('demo-api')['status'], 500)
        self.assertEqual(self.lab.request('demo-worker')['status'], 200)
        self.assertEqual(self.client.get('/experiments/'+row['id']).status_code, 200)
        result = self.wait(row['id'])
        self.assertEqual(result['experiment']['status'],'completed')
        self.assertGreater(sum(m['http_5xx_count'] for m in result['measurements']),0)
        self.assertEqual(self.lab.request('demo-api')['status'],200)

    def test_latency_is_measured(self):
        row = self.engine.save(self.data('latency',400,2))
        self.engine.start(row['id'])
        result = self.wait(row['id'])
        self.assertTrue(any(m['avg_response_ms'] >= 400 for m in result['measurements']))

    def test_unavailability_is_connection_failure(self):
        row = self.engine.save(self.data('unavailability',100))
        self.engine.start(row['id'])
        result = self.wait(row['id'])
        self.assertGreater(sum(m['connection_error_count'] for m in result['measurements']),0)
        self.assertEqual(result['latest']['availability'],0)

    def test_overload_generates_real_bounded_http_traffic(self):
        row = self.engine.save(self.data('overload',50,2))
        with patch.object(self.lab,'request',wraps=self.lab.request) as measured:
            self.engine.start(row['id'])
            result = self.wait(row['id'])
            probes = sum(m['request_count'] for m in result['measurements'])
            self.assertGreater(measured.call_count, probes+15)
            self.assertLess(measured.call_count,150)
        self.assertEqual(result['experiment']['status'],'completed')

    def test_stop_is_idempotent_and_blocks_parameter_edits(self):
        row = self.engine.save(self.data(duration=30))
        self.engine.start(row['id'])
        with self.assertRaises(RuleError):
            self.engine.save(self.data(intensity=20), row['id'])
        before = time.monotonic()
        self.engine.stop(row['id'])
        result = self.wait(row['id'])
        self.assertEqual(result['experiment']['status'],'stopped')
        self.assertLess(time.monotonic()-before,5)
        self.assertEqual(self.engine.stop(row['id'])['status'],'stopped')
        self.assertEqual(self.lab.request('demo-api')['status'],200)

    def test_concurrent_starts_have_one_winner(self):
        rows = [self.engine.save(self.data(duration=10)) for _ in range(2)]
        results=[]
        def start(row):
            try:
                self.engine.start(row['id'])
                results.append('ok')
            except RuleError:
                results.append('blocked')
        threads=[threading.Thread(target=start,args=(r,)) for r in rows]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertCountEqual(results,['ok','blocked'])
        active=self.engine.active()
        self.assertEqual(self.engine.start(active['id'])['id'],active['id'])
        self.engine.stop(active['id'])

    def test_aggregate_known_sample_and_no_data(self):
        samples=[dict(status=s,error=None,elapsed_ms=100) for s in [200,200,201,500]]
        samples.append(dict(status=None,error='timeout',elapsed_ms=2000))
        result=aggregate(samples)
        self.assertEqual(result['successful_count']/result['request_count']*100,60)
        self.assertEqual(result['http_5xx_count'],1)
        self.assertEqual(result['timeout_count'],1)
        self.assertEqual(result['avg_response_ms'],100)
        self.assertIsNone(aggregate([])['avg_response_ms'])

    def test_cleanup_failure_blocks_start_until_retry(self):
        row=self.engine.save(self.data())
        other=self.engine.save(self.data())
        with patch.object(self.lab,'clear',side_effect=RuntimeError('test cleanup')):
            self.engine.start(row['id'])
            self.assertEqual(self.wait(row['id'])['experiment']['status'],'cleanup_failed')
            with self.assertRaises(RuleError): self.engine.start(other['id'])
        self.assertEqual(self.engine.stop(row['id'])['status'],'stopped')

    def test_foreign_keys_and_sql_constraints(self):
        import sqlite3
        with connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM environment WHERE id='local'")

    def test_process_lock_prevents_second_runner(self):
        path=Path(self.temp.name)/'test.lock'
        guard=ProcessLock(path)
        try:
            with self.assertRaises(SystemExit): ProcessLock(path)
        finally: guard.close()

    def test_stale_telemetry_is_not_zero_availability(self):
        row=self.engine.save(self.data())
        with connect(self.path) as db:
            db.execute("UPDATE experiment SET status='running', started_at='2000-01-01T00:00:00+00:00' WHERE id=?",(row['id'],))
        result=self.engine.snapshot(row['id'])
        self.assertTrue(result['stale'])
        self.assertIsNone(result['latest'])

    def test_real_process_restart_preserves_data_and_recovers_interrupted_test(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        root=Path(__file__).resolve().parents[1]
        def launch():
            return subprocess.Popen([sys.executable,str(root/'app.py'),'run','--database',str(self.path),'--port',str(port)],
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        base=f'http://127.0.0.1:{port}'
        def ready():
            for _ in range(50):
                try:
                    with opener.open(base+'/',timeout=1) as response:
                        return response.read().decode()
                except OSError: time.sleep(.1)
            self.fail('Serwer nie wystartował')
        def post(path,data,token):
            request=Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':token})
            with opener.open(request,timeout=5) as response:
                return json.load(response)
        process=launch()
        try:
            token=re.search(r'name="csrf-token" content="([^"]+)"',ready()).group(1)
            row=post('/api/experiments', self.data(duration=30),token)
            post('/api/experiments/'+row['id']+'/start',{},token)
            for _ in range(80):
                with opener.open(base+'/api/experiments/'+row['id'],timeout=2) as response:
                    result=json.load(response)
                if result['measurements']: break
                time.sleep(.1)
            self.assertTrue(result['measurements'])
            self.assertEqual(result['experiment']['status'],'running')
            process.terminate()
            process.wait(timeout=5)
            process=launch()
            ready()
            with opener.open(base+'/api/experiments/'+row['id'],timeout=2) as response:
                result=json.load(response)
            self.assertEqual(result['experiment']['status'],'failed')
            self.assertIn('Przerwany proces', result['experiment']['error_message'])
            self.assertTrue(result['measurements'])
        finally:
            process.terminate()
            process.wait(timeout=5)
        self.assertEqual(self.engine.get(row['id'])['fault_type'],'http_500')


if __name__=='__main__':
    unittest.main(verbosity=2)
