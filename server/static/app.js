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
      connBadge.textContent = '接続中';
      connBadge.className = 'badge connected';
    } else if (data.connected === false) {
      connBadge.textContent = `接続断 (最後に成功: ${fmtTime(data.last_success_at)})`;
      connBadge.className = 'badge disconnected';
    } else {
      connBadge.textContent = '不明';
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
      phaseBadge.textContent = '不明';
      phaseBadge.className = 'badge';
    }
  }
  if (blockedBy) {
    blockedBy.textContent = (status && status.blocked_by) ? `他のプログラムが動作中: ${status.blocked_by}` : '';
  }

  const daqInfo = document.getElementById('daq-info');
  if (daqInfo) {
    const daq = status && status.daq;
    if (daq) {
      const elapsed = daq.started_at ? (data.server_time - daq.started_at) : null;
      daqInfo.innerHTML = `
        <p>run: ${daq.run ?? '-'} / period: ${daq.period ?? '-'} / file: ${daq.file_id ?? '-'}</p>
        <p>有効ファイル: ${daq.valid_files ?? '-'} / ${daq.file_num ?? '-'}</p>
        <p>event_num: ${daq.event_num ?? '-'} / SCI: ${daq.sci ? 'あり' : 'なし'}</p>
        <p>経過時間: ${fmtElapsed(elapsed)}</p>
      `;
    } else {
      daqInfo.innerHTML = `<p>DAQは動いていません (latest_run: ${(status && status.latest_run) || '-'})</p>`;
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
      boardProgress.innerHTML = '<p class="muted">取得中のボードはありません</p>';
    } else {
      boardProgress.innerHTML = names.map((name) => {
        const events = boards[name].events;
        const pct = eventNum ? Math.min(100, Math.round(100 * events / eventNum)) : 0;
        const cls = lagging.has(name) ? 'lagging' : '';
        return `<p class="${cls}">${name}: ${events} / ${eventNum ?? '-'} (${pct}%)${lagging.has(name) ? ' [遅れ]' : ''}</p>`;
      }).join('');
      if (progress && progress.stale) {
        boardProgress.innerHTML += '<p class="error">進捗の更新が止まっています</p>';
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
        <p class="${autoresetOk ? '' : 'error'}">LV自動リセットモニタ: ${monitor.autoreset_running ? '生存' : '停止'}</p>
        <p class="${vetoOk ? '' : 'error'}">veto: ${monitor.veto && monitor.veto.asserted ? 'assert中' : '非assert'}${monitor.veto && monitor.veto.failed ? ' (失敗)' : ''}</p>
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

function setupStartForm() {
  const form = document.getElementById('start-form');
  if (!form) return;

  const suggestBtn = document.getElementById('suggest-run-btn');
  suggestBtn.addEventListener('click', async () => {
    const res = await fetch('/api/suggest_run_name', { credentials: 'same-origin' });
    const data = await res.json();
    document.getElementById('start-run').value = data.run;
  });

  const presetSelect = document.getElementById('start-preset');
  if (presetSelect) {
    presetSelect.addEventListener('change', () => {
      if (presetSelect.value) document.getElementById('start-event-num').value = presetSelect.value;
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const run = document.getElementById('start-run').value;
    if (!confirm(`run "${run}" でDAQを開始します。よろしいですか?`)) return;

    const body = { run: run, sci: document.getElementById('start-sci').checked };
    const fileNum = document.getElementById('start-file-num').value;
    const eventNum = document.getElementById('start-event-num').value;
    const configFrom = document.getElementById('start-config-from').value;
    if (fileNum) body.file_num = parseInt(fileNum, 10);
    if (eventNum) body.event_num = parseInt(eventNum, 10);
    if (configFrom) body.config_from = configFrom;

    const result = document.getElementById('start-result');
    result.textContent = '開始を要求しています...';
    const res = await postJSON('/daq/start', body);
    if (res.ok) {
      result.textContent = '開始を要求しました。running になるまでお待ちください。';
    } else {
      const err = res.data && res.data.error;
      result.textContent = `開始に失敗しました: ${err ? err.code + ' ' + err.message : res.status}`;
    }
  });
}

function setupStopButton() {
  const btn = document.getElementById('stop-btn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    if (!confirm('DAQを停止します。よろしいですか?')) return;
    const result = document.getElementById('stop-result');
    result.textContent = '停止を要求しています...';
    const res = await postJSON('/daq/stop');
    if (res.ok) {
      result.textContent = '停止を要求しました。後処理には数十秒かかることがあります。';
    } else {
      const err = res.data && res.data.error;
      result.textContent = `停止に失敗しました: ${err ? err.code + ' ' + err.message : res.status}`;
    }
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
  setupStopButton();
  setupNotificationAck();
});
