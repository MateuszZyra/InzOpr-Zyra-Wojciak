import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .db import ACTIVE, SERVICES, aggregate, connect, now

SCENARIOS = {
    'http_500': dict(label='Błędy HTTP 500', unit='%', minimum=1, maximum=100, default=50, description='Zwracaj błąd dla wybranej części żądań.'),
    'latency': dict(label='Opóźnienie odpowiedzi', unit='ms', minimum=1, maximum=5000, default=500, description='Sprawdź reakcję na wolniejszą usługę.'),
    'overload': dict(label='Przeciążenie', unit='żądań/s', minimum=1, maximum=50, default=20, description='Wyślij ograniczony ruch do usługi demo.'),
    'unavailability': dict(label='Niedostępność', unit='%', minimum=100, maximum=100, default=100, description='Czasowo przerwij połączenia z usługą.'),
}


class RuleError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def validate(data):
    service, kind = data.get('service_id'), data.get('fault_type')
    if service not in SERVICES:
        raise RuleError('Wybierz usługę z laboratorium.')
    if kind not in SCENARIOS:
        raise RuleError('Wybierz poprawny scenariusz.')
    values = []
    for key in ('intensity', 'duration_seconds'):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isascii() or not str(value).isdigit():
            raise RuleError('Intensywność i czas muszą być liczbami całkowitymi.')
        if len(str(value)) > 6:
            raise RuleError('Wartość przekracza dopuszczalny zakres.')
        values.append(int(value))
    intensity, duration = values
    spec = SCENARIOS[kind]
    if not spec['minimum'] <= intensity <= spec['maximum']:
        raise RuleError(f"Intensywność musi wynosić {spec['minimum']}–{spec['maximum']} {spec['unit']}.")
    if not 1 <= duration <= 300:
        raise RuleError('Czas trwania musi wynosić od 1 do 300 s.')
    return service, kind, intensity, duration


class Engine:
    def __init__(self, path, lab, window=5, interval=1):
        self.path, self.lab = path, lab
        self.window, self.interval = window, interval
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.current_id = None
        # Zakłócenia istnieją wyłącznie w pamięci nowego procesu laboratorium.
        with connect(path) as db:
            db.execute("UPDATE experiment SET status='failed', ended_at=?, error_message=? WHERE status IN ('starting','running','stopping','cleanup_failed')",
                       (now(), 'Przerwany proces aplikacji; nowe laboratorium nie zawiera poprzednich zakłóceń.'))

    def get(self, identifier):
        with connect(self.path) as db:
            row = db.execute('SELECT * FROM experiment WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise RuleError('Nie znaleziono eksperymentu.', 404)
        return dict(row)

    def active(self):
        with connect(self.path) as db:
            row = db.execute("SELECT * FROM experiment WHERE status IN ('starting','running','stopping','cleanup_failed')").fetchone()
        return dict(row) if row else None

    def readiness(self):
        healthy = self.lab.alive and self.lab.thread.is_alive()
        services = []
        for name in SERVICES:
            result = self.lab.request(name) if healthy else {'status': None}
            services.append(dict(id=name, name=name, status='available' if result['status'] == 200 else 'unavailable'))
        with connect(self.path) as db:
            db.execute('UPDATE environment SET status=?,isolation_verified=?,checked_at=? WHERE id=?',
                       ('ready' if healthy else 'unavailable', 0, now(), 'local'))
            for service in services:
                db.execute('UPDATE service SET status=?, checked_at=? WHERE id=?', (service['status'], now(), service['id']))
        return dict(ready=healthy, services=services, active=self.active(), mode='local-demo',
                    target_scope_verified=healthy, isolation_verified=False)

    def save(self, data, identifier=None):
        values = validate(data)
        with self.lock, connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            if identifier:
                row = db.execute('SELECT status FROM experiment WHERE id=?', (identifier,)).fetchone()
                if row is None:
                    raise RuleError('Nie znaleziono konfiguracji.', 404)
                if row['status'] != 'draft':
                    raise RuleError('Można edytować tylko nieuruchomiony eksperyment.', 409)
                db.execute('UPDATE experiment SET service_id=?,fault_type=?,intensity=?,duration_seconds=? WHERE id=?', (*values, identifier))
            else:
                identifier = str(uuid.uuid4())
                db.execute('INSERT INTO experiment(id,service_id,fault_type,intensity,duration_seconds,status,created_at) VALUES (?,?,?,?,?,?,?)',
                           (identifier, *values, 'draft', now()))
        return self.get(identifier)

    def start(self, identifier):
        with self.lock:
            row = self.get(identifier)
            if row['status'] in ('starting', 'running', 'stopping'):
                return row
            if row['status'] != 'draft':
                raise RuleError('Ten eksperyment został już zakończony.', 409)
            if self.active():
                raise RuleError('Inny eksperyment jest aktywny lub wymaga usunięcia zakłócenia.', 409)
            state = self.readiness()
            if not state['ready'] or next(s for s in state['services'] if s['id'] == row['service_id'])['status'] != 'available':
                raise RuleError('Usługa lub laboratorium nie są gotowe.', 409)
            with connect(self.path) as db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute("SELECT 1 FROM experiment WHERE status IN ('starting','running','stopping','cleanup_failed')").fetchone():
                    raise RuleError('Inny eksperyment jest aktywny.', 409)
                db.execute("UPDATE experiment SET status='starting' WHERE id=?", (identifier,))
            try:
                self.lab.apply(row['service_id'], row['fault_type'], row['intensity'], row['duration_seconds'])
                started = datetime.now(timezone.utc)
                with connect(self.path) as db:
                    db.execute("UPDATE experiment SET status='running',started_at=?,deadline_at=? WHERE id=?",
                               (started.isoformat(), (started+timedelta(seconds=row['duration_seconds'])).isoformat(), identifier))
                self.stop_event = threading.Event()
                self.current_id = identifier
                self.thread = threading.Thread(target=self._run, args=(self.get(identifier),), daemon=True, name='experiment')
                self.thread.start()
            except Exception as exc:
                self._finish(row, 'failed', str(exc))
                raise RuleError('Nie udało się uruchomić eksperymentu.', 503) from exc
        return self.get(identifier)

    def stop(self, identifier):
        with self.lock:
            row = self.get(identifier)
            if row['status'] in ('completed', 'stopped', 'failed'):
                return row
            if row['status'] == 'cleanup_failed':
                self._finish(row, 'stopped')
                return self.get(identifier)
            if row['status'] == 'draft':
                raise RuleError('Eksperyment nie został uruchomiony.', 409)
            with connect(self.path) as db:
                db.execute("UPDATE experiment SET status='stopping' WHERE id=?", (identifier,))
            self.stop_event.set()
            # Od razu zdejmij opóźnienia i przerwy w dostępności.
            try:
                self.lab.clear(row['service_id'])
            except Exception:
                pass  # _finish zapisze potwierdzony wynik sprzątania.
        return self.get(identifier)

    def _persist(self, identifier, start, samples):
        if not samples:
            return
        metrics = aggregate(samples)
        with connect(self.path) as db:
            db.execute('''INSERT INTO measurement(experiment_id,window_start,window_end,request_count,response_count,
                       http_5xx_count,timeout_count,connection_error_count,successful_count,avg_response_ms)
                       VALUES (?,?,?,?,?,?,?,?,?,?)''', (identifier, start, now(), *metrics.values()))

    def _finish(self, row, status, error=None):
        try:
            self.lab.clear(row['service_id'])
        except Exception as exc:
            status, error = 'cleanup_failed', 'Nie potwierdzono usunięcia zakłócenia: ' + str(exc)
        with connect(self.path) as db:
            db.execute('UPDATE experiment SET status=?,ended_at=?,error_message=? WHERE id=?', (status, now(), error, row['id']))

    def _load(self, row, stop):
        deadline = time.monotonic() + max(0, (datetime.fromisoformat(row['deadline_at'])-datetime.now(timezone.utc)).total_seconds())
        with ThreadPoolExecutor(max_workers=10, thread_name_prefix='load') as pool:
            pending = set()
            while not stop.is_set() and time.monotonic() < deadline:
                pending = {f for f in pending if not f.done()}
                if len(pending) < 10:
                    pending.add(pool.submit(self.lab.request, row['service_id']))
                stop.wait(1/row['intensity'])

    def _run(self, row):
        samples, window_start, window_tick = [], now(), time.monotonic()
        loader_stop = threading.Event()
        loader = None
        status, error = 'completed', None
        try:
            if row['fault_type'] == 'overload':
                loader = threading.Thread(target=self._load, args=(row, loader_stop), daemon=True)
                loader.start()
            deadline = datetime.fromisoformat(row['deadline_at']).timestamp()
            while not self.stop_event.is_set() and time.time() < deadline:
                if time.monotonic()-window_tick >= self.window:
                    self._persist(row['id'], window_start, samples)
                    samples, window_start, window_tick = [], now(), time.monotonic()
                tick = time.monotonic()
                samples.append(self.lab.request(row['service_id']))
                self.stop_event.wait(min(max(0, self.interval-(time.monotonic()-tick)), max(0, deadline-time.time())))
            if self.stop_event.is_set():
                status = 'stopped'
        except Exception as exc:
            status, error = 'failed', 'Błąd zbierania danych: ' + str(exc)
        finally:
            loader_stop.set()
            if loader:
                loader.join(timeout=3)
            try:
                self._persist(row['id'], window_start, samples)
            except Exception as exc:
                status, error = 'failed', 'Błąd zapisu pomiarów: ' + str(exc)
            with self.lock:
                self._finish(row, status, error)

    def snapshot(self, identifier):
        row = self.get(identifier)
        with connect(self.path) as db:
            measurements = [dict(m) for m in db.execute('SELECT * FROM measurement WHERE experiment_id=? ORDER BY id DESC LIMIT 12', (identifier,))]
        for m in measurements:
            m['availability'] = round(100*m['successful_count']/m['request_count'], 1) if m['request_count'] else None
        latest = measurements[0] if measurements else None
        last_time = latest['window_end'] if latest else row['started_at']
        stale = row['status'] in ('running','stopping') and bool(last_time) and (datetime.now(timezone.utc)-datetime.fromisoformat(last_time)).total_seconds() > 10
        remaining = max(0, (datetime.fromisoformat(row['deadline_at'])-datetime.now(timezone.utc)).total_seconds()) if row['deadline_at'] and row['status'] in ACTIVE else 0
        return dict(experiment=row, measurements=measurements, latest=latest, stale=stale, remaining=round(remaining), server_time=now())

    def close(self):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=5)
