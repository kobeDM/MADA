import json
import time

from fastapi.testclient import TestClient

import mada_client_files
import mada_client_ops
from conftest import HOME, make_run


def wait_phase(api, phase, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = api.get('/api/v1/status').json()
        if status['phase'] == phase:
            return status
        time.sleep(0.2)
    raise AssertionError(f"phase did not become {phase}: {api.get('/api/v1/status').json()}")


def test_auth(client):
    api, settings = client
    anon = TestClient(api.app)
    assert anon.get('/api/v1/status').status_code == 401
    assert anon.get('/api/v1/status', headers={'Authorization': 'Bearer wrong'}).json()['error']['code'] == 'unauthorized'
    assert anon.get('/api/v1/health').json() == {'ok': True, 'api_version': 1}
    settings.allowed_servers = ['10.0.0.1']
    resp = api.get('/api/v1/status')
    assert resp.status_code == 403 and resp.json()['error']['code'] == 'forbidden_origin'


def test_idle_status(client):
    api, _ = client
    status = api.get('/api/v1/status').json()
    assert status['phase'] == 'idle' and status['daq'] is None and status['last_exit'] is None
    assert status['monitor']['autoreset_running'] is True and status['latest_run'] is None
    progress = api.get('/api/v1/progress').json()
    assert progress['boards'] == {} and progress['stale'] is False


def test_runs_files_warnings_config(client):
    api, _ = client
    make_run('runA')
    make_run('runB', config=False, periods=2)
    mada_client_files.clear_cache()
    runs = api.get('/api/v1/runs').json()['runs']
    assert {r['run'] for r in runs} == {'runA', 'runB'}
    assert {r['run']: r['has_config'] for r in runs} == {'runA': True, 'runB': False}
    assert [r['run'] for r in runs][0] == api.get('/api/v1/status').json()['latest_run']

    files = api.get('/api/v1/runs/runA/periods/0/files').json()['files']
    assert [f['file_id'] for f in files] == [0, 1]
    assert files[0]['valid'] is True and files[1]['valid'] is False and files[1]['invalid_reason'] == 'reader died'
    assert files[0]['boards']['B1']['size'] == 2000 and files[0]['end'] == 101.0
    assert [f['file_id'] for f in api.get('/api/v1/runs/runA/periods/0/files?after=0').json()['files']] == [1]

    with open(f'{HOME}/data/runA/per0000/warnings.log', 'w') as f:
        f.write('10.000\t2026-11-12T10:00:00.000\t0001\tB2\tWARNING t=10.000 kind=board_lag events=3\n')
        f.write('20.000\t2026-11-12T10:00:10.000\t0001\tDAQ\tplain message\n')
        f.write('30.000\t2026-11-12T10:00:20.000\t0002\tDAQ\tunfinished')
    records = api.get('/api/v1/runs/runA/periods/0/warnings').json()['records']
    assert [r['kind'] for r in records] == ['board_lag', None] and records[0]['level'] == 'WARNING'
    assert len(api.get('/api/v1/runs/runA/periods/0/warnings?after=10').json()['records']) == 1

    assert api.get('/api/v1/runs/runA/config').json()['gigaIwaki']['B1']['IP'] == '1.1.1.1'
    assert api.get('/api/v1/runs/runB/config').status_code == 404
    assert api.get('/api/v1/runs/nope/periods/0/files').status_code == 404
    assert api.get('/api/v1/runs/runA/periods/9/files').status_code == 404
    assert api.get('/api/v1/runs/..%2f..%2fetc/config').status_code in (404, 422)


def test_log_tail(client):
    api, _ = client
    with open(f'{HOME}/run/runA_0000.log', 'w', encoding='utf-8') as f:
        f.write('line1\nline2\n')
    first = api.get('/api/v1/log').json()
    assert first['file'] == 'runA_0000.log' and first['text'] == 'line1\nline2\n'
    with open(f'{HOME}/run/runA_0000.log', 'a', encoding='utf-8') as f:
        f.write('line3\n')
    second = api.get(f"/api/v1/log?offset={first['offset']}").json()
    assert second['text'] == 'line3\n'
    assert api.get('/api/v1/log?offset=99999').json()['text'].startswith('line1')


def test_start_validation(client):
    api, _ = client
    make_run('runA')
    mada_client_files.clear_cache()
    assert api.post('/api/v1/daq/start', json={'file_num': 0}).json()['error']['code'] == 'invalid_request'
    assert api.post('/api/v1/daq/start', json={'file_num': 101}).json()['error']['code'] == 'invalid_request'
    assert api.post('/api/v1/daq/start', json={'run': '../x'}).json()['error']['code'] == 'invalid_request'
    assert api.post('/api/v1/daq/start', json={'bogus': 1}).status_code == 422
    resp = api.post('/api/v1/daq/start', json={'run': 'runA', 'config_from': 'runA'})
    assert resp.status_code == 422 and 'config_from' in resp.json()['error']['message']
    resp = api.post('/api/v1/daq/start', json={'run': 'fresh', 'config_from': 'ghost'})
    assert resp.json()['error']['code'] == 'invalid_request' or resp.status_code in (404, 422)
    assert api.post('/api/v1/daq/stop').json()['error']['code'] == 'not_running'


def test_start_new_run_without_source(client):
    api, _ = client
    resp = api.post('/api/v1/daq/start', json={'run': 'first'})
    assert resp.status_code == 422 and resp.json()['error']['code'] == 'config_not_found'


def test_start_run_stop(client):
    api, _ = client
    make_run('runA')
    mada_client_files.clear_cache()
    resp = api.post('/api/v1/daq/start', json={'run': 'runA', 'file_num': 2, 'event_num': 1000})
    assert resp.status_code == 202 and resp.json() == {'phase': 'starting'}

    status = wait_phase(api, 'running')
    daq = status['daq']
    assert daq['run'] == 'runA' and daq['file_num'] == 2 and daq['event_num'] == 1000 and daq['sci'] is False
    assert daq['period'] == 1 and [b['id'] for b in daq['boards']] == ['SIM-1', 'SIM-2'] or len(daq['boards']) == 2
    assert daq['started_at'] is not None
    assert api.post('/api/v1/daq/start', json={'run': 'runA'}).json()['error']['code'] == 'busy'

    deadline = time.time() + 5
    while time.time() < deadline:
        progress = api.get('/api/v1/progress').json()
        if progress['boards']:
            break
        time.sleep(0.1)
    assert progress['stale'] is False and progress['event_num'] == 1000 and len(progress['boards']) == 2

    deadline = time.time() + 5
    while time.time() < deadline and not api.get('/api/v1/runs/runA/periods/1/files').json()['files']:
        time.sleep(0.1)
    assert api.post('/api/v1/daq/stop').json() == {'phase': 'stopping'}
    assert api.post('/api/v1/daq/stop').json() == {'phase': 'stopping'}
    assert api.get('/api/v1/status').json()['daq']['stop_requested_at'] is not None
    final = wait_phase(api, 'idle')
    assert final['last_exit']['reason'] == 'stopped' and final['last_exit']['run'] == 'runA'
    assert api.get('/api/v1/progress').json()['boards'] == {}
    files = api.get('/api/v1/runs/runA/periods/1/files').json()['files']
    assert files and all(f['valid'] for f in files)
    log = open(f'{HOME}/run/mada_client.log').read()
    assert 'start' in log and 'stop' in log


def test_new_run_copies_config(client):
    api, _ = client
    make_run('runA')
    mada_client_files.clear_cache()
    assert api.post('/api/v1/daq/start', json={'run': 'runNew', 'file_num': 1}).status_code == 202
    wait_phase(api, 'running')
    with open(f'{HOME}/data/runNew/MADA_config.json') as f:
        assert json.load(f)['gigaIwaki']['B1']['IP'] == '1.1.1.1'
    api.post('/api/v1/daq/stop')
    wait_phase(api, 'idle')


def test_error_exit_and_crash(client):
    api, settings = client
    make_run('runA')
    mada_client_files.clear_cache()
    settings.sim_env['MADA_SIM_FAIL_AFTER'] = '1'
    api.post('/api/v1/daq/start', json={'run': 'runA'})
    status = wait_phase(api, 'idle')
    assert status['last_exit']['reason'] == 'error' and 'simulated failure' in status['last_exit']['message']

    settings.sim_env['MADA_SIM_FAIL_AFTER'] = '0'
    api.post('/api/v1/daq/start', json={'run': 'runA'})
    wait_phase(api, 'running')
    import os, signal
    pid = api.get('/api/v1/status').json()['daq']['pid']
    os.kill(pid, signal.SIGKILL)
    final = wait_phase(api, 'idle')
    assert final['last_exit']['reason'] == 'crashed'


def test_lag_and_invalid_file(client):
    api, settings = client
    make_run('runA')
    mada_client_files.clear_cache()
    settings.sim_env.update({'MADA_SIM_LAG': '1', 'MADA_SIM_INVALID_FILE': '0'})
    api.post('/api/v1/daq/start', json={'run': 'runA', 'file_num': 1})
    wait_phase(api, 'running')
    time.sleep(1.5)
    records = api.get('/api/v1/runs/runA/periods/1/warnings').json()['records']
    assert records and records[0]['kind'] == 'board_lag'
    files = api.get('/api/v1/runs/runA/periods/1/files').json()['files']
    assert files[0]['valid'] is False and files[0]['invalid_reason']
    api.post('/api/v1/daq/stop')
    wait_phase(api, 'idle')


def test_scaler_state(client):
    api, _ = client
    assert api.get('/api/v1/status').json()['monitor']['scaler'] is None
    import json
    with open(f'{HOME}/run/mada_scaler.json', 'w') as f:
        json.dump({'state': 'running', 'period': 4, 'pid': 1, 'host': 'h', 'time': 1.0}, f)
    scaler = api.get('/api/v1/status').json()['monitor']['scaler']
    assert scaler == {'state': 'orphaned', 'period': 4, 'time': 1.0}
    make_run('runA')
    mada_client_files.clear_cache()
    api.post('/api/v1/daq/start', json={'run': 'runA', 'file_num': 1})
    wait_phase(api, 'running')
    assert api.get('/api/v1/status').json()['monitor']['scaler']['state'] == 'running'
    api.post('/api/v1/daq/stop')
    wait_phase(api, 'idle')
    assert api.get('/api/v1/status').json()['monitor']['scaler']['state'] == 'stopped'


def test_soft_stop(client):
    api, settings = client
    make_run('runA')
    mada_client_files.clear_cache()
    settings.sim_env['MADA_SIM_FILE_SEC'] = '2.0'
    api.post('/api/v1/daq/start', json={'run': 'runA', 'file_num': 50, 'event_num': 1000})
    wait_phase(api, 'running')
    deadline = time.time() + 5
    while time.time() < deadline and not api.get('/api/v1/progress').json()['boards']:
        time.sleep(0.1)
    assert api.post('/api/v1/daq/stop/soft').json() == {'phase': 'stopping'}
    daq = api.get('/api/v1/status').json()['daq']
    assert daq['stop_mode'] == 'soft' and daq['stop_requested_at'] is not None
    assert api.post('/api/v1/daq/stop/soft').json() == {'phase': 'stopping'}
    final = wait_phase(api, 'idle')
    assert final['last_exit']['reason'] == 'stopped'
    files = api.get('/api/v1/runs/runA/periods/1/files').json()['files']
    assert len(files) == 1 and files[0]['valid']


def test_force_stop_refused_between_files(client, monkeypatch):
    api, _ = client
    make_run('runA')
    mada_client_files.clear_cache()
    api.post('/api/v1/daq/start', json={'run': 'runA', 'file_num': 50, 'event_num': 1000})
    wait_phase(api, 'running')
    monkeypatch.setattr(mada_client_ops, '_file_in_progress', lambda pid: False)
    resp = api.post('/api/v1/daq/stop')
    assert resp.status_code == 409 and resp.json()['error']['code'] == 'busy_file_update'
    assert api.get('/api/v1/status').json()['phase'] == 'running'
    monkeypatch.undo()
    api.post('/api/v1/daq/stop')
    wait_phase(api, 'idle')


def test_progress_while_stopping(client):
    api, settings = client
    make_run('runA')
    mada_client_files.clear_cache()
    settings.sim_env['MADA_SIM_FILE_SEC'] = '3.0'
    api.post('/api/v1/daq/start', json={'run': 'runA', 'file_num': 50, 'event_num': 1000})
    wait_phase(api, 'running')
    deadline = time.time() + 5
    while time.time() < deadline and not api.get('/api/v1/progress').json()['boards']:
        time.sleep(0.1)
    api.post('/api/v1/daq/stop/soft')
    assert api.get('/api/v1/status').json()['phase'] == 'stopping'
    assert api.get('/api/v1/progress').json()['boards']
    api.post('/api/v1/daq/stop')
    assert api.get('/api/v1/progress').json()['boards'] == {}
    wait_phase(api, 'idle')
