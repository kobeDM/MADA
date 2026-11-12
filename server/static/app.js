function getCookie(name) {
  const match = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
  return match ? decodeURIComponent(match[1]) : null;
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCookie('mada_csrf') || '',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data = null;
  try { data = await response.json(); } catch (e) { /* no body */ }
  return { ok: response.ok, status: response.status, data: data };
}

function fmtTime(epoch) {
  if (epoch === null || epoch === undefined) return '-';
  return new Date(epoch * 1000).toLocaleString('ja-JP');
}

function fmtElapsed(seconds) {
  if (seconds === null || seconds === undefined || seconds < 0) return '-';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

function renderState(data) {
  const connBadge = document.getElementById('connection-badge');
  if (connBadge) {
    if (data.connected === true) {
      connBadge.textContent = 'Connected';
      connBadge.className = 'badge connected';
    } else if (data.connected === false) {
      connBadge.textContent = `Disconnected (last success: ${fmtTime(data.last_success_at)})`;
      connBadge.className = 'badge disconnected';
    } else {
      connBadge.textContent = 'Unknown';
      connBadge.className = 'badge';
    }
  }

  const status = data.status;
  const phaseBadge = document.getElementById('phase-badge');
  const blockedBy = document.getElementById('blocked-by');
  if (phaseBadge) {
    if (status) {
      phaseBadge.textContent = status.phase;
      phaseBadge.className = 'badge ' + status.phase;
    } else {
      phaseBadge.textContent = 'Unknown';
      phaseBadge.className = 'badge';
    }
  }
  if (blockedBy) {
    blockedBy.textContent = (status && status.blocked_by) ? `Another program is running: ${status.blocked_by}` : '';
  }

  const daqInfo = document.getElementById('daq-info');
  if (daqInfo) {
    const daq = status && status.daq;
    if (daq) {
      // status.time is the daq-client's own clock, taken at the same moment
      // as started_at/stop_requested_at -- server_time (this server's clock)
      // would drift with any clock skew between the two machines (server
      // spec section 4: the display must stay consistent even when the two
      // clocks differ).
      const clientNow = status.time;
      const elapsed = daq.started_at ? (clientNow - daq.started_at) : null;
      let stoppingNotice = '';
      if (status.phase === 'stopping' && daq.stop_requested_at) {
        const stoppingFor = clientNow - daq.stop_requested_at;
        stoppingNotice = `<p>Time since stop request: ${fmtElapsed(stoppingFor)}</p>`;
        if (daq.stop_mode === 'soft') {
          stoppingNotice += `<p>Soft stop: the DAQ stops when file ${daq.file_id ?? '-'} is complete.</p>`;
        } else if (stoppingFor > 120) {
          stoppingNotice += '<p class="error">Cleanup is taking long. You may need to check the terminal.</p>';
        }
      }
      daqInfo.innerHTML = `
        <p>run: ${daq.run ?? '-'} / period: ${daq.period ?? '-'} / file: ${daq.file_id ?? '-'}</p>
        <p>Valid files: ${daq.valid_files ?? '-'} / ${daq.file_num ?? '-'}</p>
        <p>event_num: ${daq.event_num ?? '-'} / SCI: ${daq.sci ? 'yes' : 'no'}</p>
        <p>Elapsed: ${fmtElapsed(elapsed)}</p>
        ${stoppingNotice}
      `;
    } else {
      daqInfo.innerHTML = `<p>DAQ is not running (latest_run: ${(status && status.latest_run) || '-'})</p>`;
    }
  }

  const boardProgress = document.getElementById('board-progress');
  if (boardProgress) {
    const progress = data.progress;
    const boards = (progress && progress.boards) || {};
    const eventNum = progress && progress.event_num;
    const lagging = new Set((progress && progress.lagging) || []);
    const names = Object.keys(boards);
    if (names.length === 0) {
      boardProgress.innerHTML = '<p class="muted">No boards are acquiring</p>';
    } else {
      boardProgress.innerHTML = names.map((name) => {
        const events = boards[name].events;
        const pct = eventNum ? Math.min(100, Math.round(100 * events / eventNum)) : 0;
        const cls = lagging.has(name) ? 'lagging' : '';
        return `<p class="${cls}">${name}: ${events} / ${eventNum ?? '-'} (${pct}%)${lagging.has(name) ? ' [lagging]' : ''}</p>`;
      }).join('');
      if (progress && progress.stale) {
        boardProgress.innerHTML += '<p class="error">Progress updates have stopped</p>';
      }
    }
  }

  const monitorInfo = document.getElementById('monitor-info');
  if (monitorInfo) {
    const monitor = status && status.monitor;
    if (monitor) {
      const autoresetOk = monitor.autoreset_running !== false;
      const vetoOk = !(monitor.veto && monitor.veto.failed);
      monitorInfo.innerHTML = `
        <p class="${autoresetOk ? '' : 'error'}">LV auto-reset monitor: ${monitor.autoreset_running ? 'alive' : 'stopped'}</p>
        <p class="${vetoOk ? '' : 'error'}">veto: ${monitor.veto && monitor.veto.asserted ? 'asserted' : 'not asserted'}${monitor.veto && monitor.veto.failed ? ' (failed)' : ''}</p>
      `;
    } else {
      monitorInfo.innerHTML = '<p class="muted">-</p>';
    }
  }

  const lastExitCard = document.getElementById('last-exit-card');
  const lastExit = document.getElementById('last-exit');
  if (lastExitCard && lastExit) {
    const exit = status && status.last_exit;
    if (exit) {
      lastExitCard.style.display = '';
      const cls = exit.reason === 'stopped' ? '' : 'error';
      lastExit.innerHTML = `<p class="${cls}">${exit.reason}: ${exit.message || ''} (${fmtTime(exit.time)}, run ${exit.run} per${exit.period})</p>`;
    } else {
      lastExitCard.style.display = 'none';
    }
  }

  fillRunDefault(status);
  renderControls(data);
  renderOperationMessages(data);
}

function subscribeState() {
  const initial = document.getElementById('initial-state');
  if (initial) {
    try { renderState(JSON.parse(initial.textContent)); } catch (e) { /* ignore */ }
  }
  const source = new EventSource('/api/state');
  source.onmessage = (e) => {
    try { renderState(JSON.parse(e.data)); } catch (err) { /* ignore malformed event */ }
  };
}

// Operation messages follow the phase the server reports, not just the HTTP
// answer: "202 accepted" only means the request was taken.
let startPending = null;  // {at: ms, seenStarting: bool}
let stopPending = null;   // 'soft' | 'force'

function byId(id) { return document.getElementById(id); }

function fillRunDefault(status) {
  const input = byId('start-run');
  if (!input || !status || !status.latest_run || input.dataset.touched === '1') return;
  input.value = status.latest_run;
}

function renderControls(data) {
  const c = data.controls;
  if (!c) return;
  const pairs = [['start-btn', c.start], ['soft-stop-btn', c.soft_stop], ['force-stop-btn', c.force_stop]];
  pairs.forEach(([id, ctl]) => {
    const el = byId(id);
    if (!el) return;
    el.disabled = !ctl.enabled;
    el.title = ctl.enabled ? '' : (ctl.reason || '');
  });
  const startHint = byId('start-hint');
  if (startHint) startHint.textContent = c.start.enabled ? '' : (c.start.reason || '');
  const stopHint = byId('stop-hint');
  if (stopHint) {
    if (!c.soft_stop.enabled) stopHint.textContent = c.soft_stop.reason || '';
    else if (!c.force_stop.enabled) stopHint.textContent = `Force stop is not available now: ${c.force_stop.reason}`;
    else stopHint.textContent = '';
  }
}

function renderOperationMessages(data) {
  const status = data.status;
  if (!status) return;
  const phase = status.phase;
  const daq = status.daq || {};

  const startResult = byId('start-result');
  if (startResult && startPending) {
    if (phase === 'starting') {
      startPending.seenStarting = true;
      startResult.textContent = 'DAQ is starting: powering on the boards and setting DAC/Vth. No file is acquired yet.';
    } else if (phase === 'running') {
      startResult.textContent = `DAQ started and is running (run ${daq.run ?? '-'}, file ${daq.file_id ?? '-'}).`;
      startPending = null;
    } else if (phase === 'idle' && (startPending.seenStarting || Date.now() - startPending.at > 30000)) {
      startResult.textContent = 'The DAQ is not running. It did not start or ended right after starting; see "Last exit" and the log.';
      startPending = null;
    }
  }

  const stopResult = byId('stop-result');
  if (stopResult && stopPending) {
    if (phase === 'idle') {
      stopResult.textContent = 'DAQ stopped.';
      stopPending = null;
    } else if (daq.stop_mode === 'soft' || (stopPending === 'soft' && phase === 'running')) {
      stopResult.textContent = `Soft stop requested: the DAQ stops when file ${daq.file_id ?? '-'} is complete.`;
    } else if (phase === 'stopping') {
      stopResult.textContent = 'DAQ is stopping: cleanup (DAQ enable low, power off) is in progress.';
    }
  }
}

function setupStartForm() {
  const form = byId('start-form');
  if (!form) return;

  byId('start-run').addEventListener('input', (e) => { e.target.dataset.touched = '1'; });

  const presetSelect = byId('start-preset');
  if (presetSelect) {
    presetSelect.addEventListener('change', () => {
      if (presetSelect.value) byId('start-event-num').value = presetSelect.value;
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const run = byId('start-run').value;
    if (!confirm(`Start DAQ with run "${run}". Are you sure?`)) return;

    const body = { run: run, sci: byId('start-sci').checked };
    const fileNum = byId('start-file-num').value;
    const eventNum = byId('start-event-num').value;
    if (fileNum) body.file_num = parseInt(fileNum, 10);
    if (eventNum) body.event_num = parseInt(eventNum, 10);

    const result = byId('start-result');
    result.textContent = 'Requesting start...';
    const res = await postJSON('/daq/start', body);
    if (res.ok) {
      startPending = { at: Date.now(), seenStarting: false };
      result.textContent = 'Start request accepted. Waiting for the DAQ to come up...';
    } else {
      const err = res.data && res.data.error;
      result.textContent = `Start failed: ${err ? err.code + ' ' + err.message : res.status}`;
    }
  });
}

function setupStopButtons() {
  const modes = [
    ['soft-stop-btn', 'soft', 'Stop the DAQ after the current file is complete?'],
    ['force-stop-btn', 'force', 'Force stop: stop the DAQ NOW, in the middle of the current file. Are you sure?'],
  ];
  modes.forEach(([id, mode, question]) => {
    const btn = byId(id);
    if (!btn) return;
    btn.addEventListener('click', async () => {
      if (!confirm(question)) return;
      const result = byId('stop-result');
      result.textContent = 'Requesting stop...';
      const res = await postJSON('/daq/stop', { mode: mode });
      if (res.ok) {
        stopPending = mode;
        result.textContent = mode === 'soft'
          ? 'Soft stop request accepted. Waiting for the current file to finish...'
          : 'Force stop request accepted. Waiting for the DAQ to stop...';
      } else {
        const err = res.data && res.data.error;
        result.textContent = `Stop failed: ${err ? err.code + ' ' + err.message : res.status}`;
      }
    });
  });
}

function setupNotificationAck() {
  document.querySelectorAll('.ack-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      const res = await postJSON(`/notifications/${id}/ack`, {});
      if (res.ok) {
        btn.closest('li').remove();
      }
    });
  });
}

function startLogTail() {
  const view = document.getElementById('log-view');
  const fileLabel = document.getElementById('log-file');
  let offset = null;
  let currentFile = null;

  async function tick() {
    const params = new URLSearchParams();
    if (offset !== null) params.set('offset', offset);
    try {
      const res = await fetch('/api/log?' + params.toString(), { credentials: 'same-origin' });
      const data = await res.json();
      if (data.error) {
        view.textContent += `\n[error] ${data.error.code}: ${data.error.message}\n`;
      } else {
        if (data.file !== currentFile) {
          currentFile = data.file;
          fileLabel.textContent = data.file || '';
          view.textContent = '';
        }
        view.textContent += data.text;
        view.scrollTop = view.scrollHeight;
        offset = data.offset;
      }
    } catch (e) {
      // keep retrying on the next tick
    }
  }

  tick();
  setInterval(tick, 2000);
}

document.addEventListener('DOMContentLoaded', () => {
  subscribeState();
  setupStartForm();
  setupStopButtons();
  setupNotificationAck();
});
