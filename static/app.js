const scenario = document.querySelector('#scenario');
if (scenario) {
  const update = (reset) => {
    const option = scenario.selectedOptions[0];
    const input = document.querySelector('#intensity');
    input.min = option.dataset.min; input.max = option.dataset.max;
    input.readOnly = scenario.value === 'unavailability';
    if (reset || input.readOnly) input.value = option.dataset.default;
    document.querySelector('#unit').textContent = `(${option.dataset.unit})`;
    document.querySelector('#range-help').textContent = `${option.dataset.min}–${option.dataset.max} ${option.dataset.unit}`;
    document.querySelector('#scenario-help').textContent = option.dataset.description;
  };
  scenario.addEventListener('change', () => update(true));
  update(false);
}
const monitor = document.querySelector('#monitor');
if (monitor) {
  const names = {draft:'Konfiguracja zapisana',starting:'Uruchamianie',running:'Trwa',stopping:'Zatrzymywanie',completed:'Zakończony',stopped:'Zatrzymany',failed:'Błąd',cleanup_failed:'Wymaga usunięcia zakłócenia'};
  const stopButton = document.querySelector('#stop');
  const message = document.querySelector('#monitor-message');
  let timer;
  const refresh = async () => {
    clearTimeout(timer);
    try {
      const response = await fetch(monitor.dataset.endpoint, {cache:'no-store', signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('Nie udało się pobrać pomiarów.');
      const data = await response.json();
      const row = data.experiment;
      const active = ['starting','running','stopping','cleanup_failed'].includes(row.status);
      document.querySelector('#status').textContent = names[row.status] || row.status;
      document.querySelector('#remaining').textContent = data.remaining;
      stopButton.disabled = !active || row.status === 'stopping';
      stopButton.textContent = row.status === 'cleanup_failed' ? 'Ponów usunięcie zakłócenia' : 'Zatrzymaj eksperyment';
      document.querySelector('#new-test').hidden = active;
      message.className = `notice ${data.stale || row.error_message ? 'error' : ''}`;
      message.textContent = row.error_message || (data.stale ? 'Brak aktualnych danych. Wyświetlone wartości są nieaktualne.' : active ? 'Eksperyment trwa. Monitorowanie obejmuje bieżące okno pomiarowe.' : 'Eksperyment zakończony. Zakłócenie zostało usunięte.');
      const metric = data.latest;
      document.querySelector('#response').textContent = metric?.avg_response_ms != null ? `${Math.round(metric.avg_response_ms)} ms` : '—';
      document.querySelector('#errors').textContent = metric ? metric.http_5xx_count : '—';
      document.querySelector('#availability').textContent = metric?.availability != null ? `${metric.availability}%` : '—';
      document.querySelector('#updated').textContent = metric ? `Aktualizacja: ${new Date(metric.window_end).toLocaleTimeString('pl-PL')}` : 'Oczekiwanie na pierwsze pomiary';
      const body = document.querySelector('#measurements');
      if (data.measurements.length) {
        body.replaceChildren();
        data.measurements.forEach(m => {
          const tr = document.createElement('tr');
          [new Date(m.window_end).toLocaleTimeString('pl-PL'), m.request_count, m.response_count, m.http_5xx_count, m.timeout_count, m.connection_error_count, m.avg_response_ms == null ? '—' : `${Math.round(m.avg_response_ms)} ms`].forEach(value => {
            const td = document.createElement('td'); td.textContent = value; tr.append(td);
          });
          body.append(tr);
        });
      }
      if (active) timer = setTimeout(refresh, 5000);
    } catch (error) {
      message.className = 'notice error';
      message.textContent = 'Brak połączenia z aplikacją. Wyświetlone dane mogą być nieaktualne. Próba ponownego połączenia za 5 s.';
      timer = setTimeout(refresh, 5000);
    }
  };
  stopButton.addEventListener('click', async () => {
    stopButton.disabled = true;
    try {
      const response = await fetch(monitor.dataset.stop, {method:'POST', headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content}, signal:AbortSignal.timeout(8000)});
      if (!response.ok) { const result = await response.json(); throw new Error(result.error); }
      await refresh();
    } catch (error) { message.textContent = error.message; message.className = 'notice error'; stopButton.disabled = false; }
  });
  refresh();
}
