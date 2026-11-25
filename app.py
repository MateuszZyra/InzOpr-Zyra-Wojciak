import argparse
import atexit
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from riskr.db import connect, initialize
from riskr.engine import Engine, RuleError, SCENARIOS
from riskr.laboratory import Laboratory

ROOT = Path(__file__).resolve().parent


def create_app(database=None, engine=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32), MAX_CONTENT_LENGTH=16384,
                      SESSION_COOKIE_SAMESITE='Strict', SESSION_COOKIE_HTTPONLY=True)
    path = Path(database or ROOT / 'instance' / 'riskr.sqlite3')
    initialize(path)
    if engine is None:
        lab = Laboratory()
        lab.start()
        engine = Engine(path, lab)
    app.extensions['engine'] = engine
    app.config['DATABASE'] = str(path)

    @app.before_request
    def protect():
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method == 'POST':
            origin = request.headers.get('Origin')
            if origin and urlsplit(origin).netloc != request.host:
                abort(403)
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf')
            if not token or not secrets.compare_digest(token, session['csrf']):
                abort(403)

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    @app.context_processor
    def common():
        return dict(scenarios=SCENARIOS, csrf=session.get('csrf'),
                    statuses={'draft':'Konfiguracja zapisana','starting':'Uruchamianie','running':'Trwa',
                              'stopping':'Zatrzymywanie','completed':'Zakończony','stopped':'Zatrzymany',
                              'failed':'Błąd','cleanup_failed':'Wymaga usunięcia zakłócenia'})

    @app.errorhandler(RuleError)
    def rule_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error=str(error)), error.code
        return render_template('error.html', message=str(error)), error.code

    @app.errorhandler(403)
    def forbidden(error):
        message = 'Sesja wygasła lub żądanie pochodzi z innej strony. Odśwież widok i spróbuj ponownie.'
        if request.path.startswith('/api/'):
            return jsonify(error=message), 403
        return render_template('error.html', message=message), 403

    @app.errorhandler(404)
    def missing(error):
        return render_template('error.html', message='Nie znaleziono strony.'), 404

    @app.get('/')
    def home():
        state = engine.readiness()
        with connect(path) as db:
            drafts = [dict(r) for r in db.execute("SELECT * FROM experiment WHERE status='draft' ORDER BY created_at DESC LIMIT 5")]
        return render_template('home.html', state=state, drafts=drafts, nav='home')

    @app.get('/health')
    def health():
        return jsonify(status='ok', laboratory=engine.lab.alive)

    @app.route('/experiments/new', methods=['GET','POST'])
    def configure():
        values = dict(service_id=request.args.get('service_id','demo-api'), fault_type='latency', intensity=500, duration_seconds=30)
        identifier = request.args.get('draft')
        if identifier:
            values = engine.get(identifier)
            if values['status'] != 'draft':
                return redirect(url_for('monitor', identifier=identifier))
        if request.method == 'POST':
            values = request.form.to_dict()
            identifier = values.get('id') or None
            try:
                row = engine.save(values, identifier)
                identifier = row['id']
                if values.get('action') == 'start':
                    engine.start(identifier)
                    return redirect(url_for('monitor', identifier=identifier))
                flash('Konfiguracja została zapisana. Możesz wrócić do niej po ponownym uruchomieniu aplikacji.', 'success')
                return redirect(url_for('configure', draft=identifier))
            except RuleError as exc:
                return render_template('configure.html', values=values, identifier=identifier, error=str(exc), nav='new'), exc.code
        return render_template('configure.html', values=values, identifier=identifier, nav='new')

    @app.get('/experiments/<identifier>')
    def monitor(identifier):
        data = engine.snapshot(identifier)
        if data['experiment']['status'] == 'draft':
            return redirect(url_for('configure', draft=identifier))
        return render_template('monitor.html', data=data, row=data['experiment'], nav='monitor')

    @app.get('/api/environment')
    def environment():
        return jsonify(engine.readiness())

    def json_data():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise RuleError('Oczekiwano obiektu JSON.')
        return data

    @app.post('/api/experiments')
    def save():
        data = json_data()
        return jsonify(engine.save(data, data.get('id'))), 201

    @app.post('/api/experiments/<identifier>/start')
    def start(identifier):
        return jsonify(engine.start(identifier))

    @app.post('/api/experiments/<identifier>/stop')
    def stop(identifier):
        return jsonify(engine.stop(identifier))

    @app.get('/api/experiments/<identifier>')
    def snapshot(identifier):
        return jsonify(engine.snapshot(identifier))

    return app


class ProcessLock:
    """Jeden runner na plik bazy; blokada zwalniana również po awarii procesu."""
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open('a+b')
        try:
            self.file.seek(0)
            if not self.file.read(1):
                self.file.write(b'0')
                self.file.flush()
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise SystemExit('RiskR już korzysta z tej bazy. Zatrzymaj poprzedni proces.') from exc

    def close(self):
        self.file.close()


def main():
    parser = argparse.ArgumentParser(description='RiskR — lokalne laboratorium')
    parser.add_argument('command', choices=['init-db','run'])
    parser.add_argument('--database', default=str(ROOT / 'instance' / 'riskr.sqlite3'))
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()
    path = Path(args.database).resolve()
    if args.command == 'init-db':
        initialize(path)
        print('Baza gotowa. Istniejące dane zostały zachowane.')
        return
    guard = ProcessLock(path.with_suffix('.lock'))
    app = create_app(path)
    engine = app.extensions['engine']

    def close():
        engine.close()
        engine.lab.close()
        guard.close()

    atexit.register(close)
    from waitress import serve
    host = '0.0.0.0' if os.environ.get('RISKR_CONTAINER') == '1' else '127.0.0.1'
    print(f'RiskR: http://127.0.0.1:{args.port}', flush=True)
    serve(app, host=host, port=args.port, threads=8)


if __name__ == '__main__':
    main()
