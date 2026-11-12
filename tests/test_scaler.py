import os
import signal
import stat
import sys
import time

import pytest

import mada_scaler
from mada_config import ConfigError, validate_scaler
from mada_scaler import ScalerError, ScalerRunner, count_lines

FAKE_SSH = '#!/bin/bash\nwhile [ "$#" -gt 1 ]; do shift; done\nexec bash -c "$1"\n'
FAKE_RUN_SCALER = f'''#!{sys.executable}
import os, signal, sys, time
path = os.path.join(sys.argv[1], 'per%04d' % int(sys.argv[2]))
f = open(path, 'w')
def edge(*args):
    f.write('0000\\t1\\t1\\t1\\t1\\n'); f.flush()
signal.signal(signal.SIGUSR1, edge)
while True:
    time.sleep(0.05)
'''


def write_script(path, text):
    with open(path, 'w') as f:
        f.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


@pytest.fixture
def scaler(tmp_path, monkeypatch):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    write_script(bin_dir / 'ssh', FAKE_SSH)
    write_script(bin_dir / 'runScaler', FAKE_RUN_SCALER)
    out_root = tmp_path / 'scaler'
    out_root.mkdir()
    monkeypatch.setenv('PATH', f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setattr(mada_scaler, 'FILE_WAIT', 1.0)
    monkeypatch.setattr(mada_scaler, 'LINE_WAIT', 0.5)
    settings = {'ssh': {'host': 'x@y', 'identity_file': 'key', 'connect_timeout': 5},
                'command': str(bin_dir / 'runScaler'), 'output_root': str(out_root)}
    runner = ScalerRunner(settings, run='run1')
    yield runner
    runner.stop()


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def test_start_verify_stop(scaler):
    scaler.preflight()
    scaler.start(3)
    assert os.path.exists(scaler.out_dir + '/per0003') and scaler.pid and alive(scaler.pid)
    with pytest.raises(ScalerError):
        scaler.verify_file(0)
    os.kill(scaler.pid, signal.SIGUSR1)
    scaler.verify_file(0)
    os.kill(scaler.pid, signal.SIGUSR1)
    with pytest.raises(ScalerError, match='more lines'):
        scaler.verify_file(0)
    pid = scaler.pid
    assert scaler.stop() is True and scaler.pid is None
    deadline = time.time() + 2
    while alive(pid) and time.time() < deadline:
        time.sleep(0.05)
    assert not alive(pid)
    assert scaler.stop() is True
    assert count_lines(scaler.out_dir + '/per0003') == 2


def test_refuses_to_overwrite(scaler):
    os.makedirs(scaler.out_dir)
    open(scaler.out_dir + '/per0001', 'w').write('0000\t1\t1\t1\t1\n')
    with pytest.raises(ScalerError, match='already exists'):
        scaler.start(1)
    assert scaler.pid is None and count_lines(scaler.out_dir + '/per0001') == 1


def test_start_fails_without_output_file(scaler):
    scaler.command = '/nonexistent/runScaler'
    with pytest.raises(ScalerError, match='did not create'):
        scaler.start(0)


def test_preflight_errors(scaler):
    scaler.command = '/nonexistent/runScaler'
    with pytest.raises(ScalerError, match='not executable'):
        scaler.preflight()


def test_clean_stale(scaler):
    scaler.start(5)
    pid = scaler.pid
    other = ScalerRunner({'ssh': scaler.ssh, 'command': scaler.command, 'output_root': os.path.dirname(scaler.out_dir)}, run='run1')
    other.clean_stale()
    deadline = time.time() + 2
    while alive(pid) and time.time() < deadline:
        time.sleep(0.05)
    assert not alive(pid)


def test_validate_scaler(tmp_path):
    validate_scaler({})
    validate_scaler({'SCALER': {'active': 0}})
    key = tmp_path / 'key'
    key.write_text('x')
    good = {'active': 1, 'ssh': {'host': 'a@b', 'identity_file': str(key)}, 'command': '/bin/runScaler', 'output_root': str(tmp_path)}
    validate_scaler({'SCALER': good})
    bad = dict(good, command='runScaler', output_root='/nonexistent', ssh={'identity_file': '/nonexistent'})
    with pytest.raises(ConfigError) as e:
        validate_scaler({'SCALER': bad})
    for text in ('ssh.host', 'identity_file', 'absolute path', 'output_root'):
        assert text in str(e.value)


def test_run_period_with_scaler(scaler, monkeypatch):
    import mada_file_cycle

    sent = []

    def fake_run_file(logger, file_id, boards, event_num, roles, sci=None, state_extra=None):
        if file_id not in sent:
            os.kill(scaler.pid, signal.SIGUSR1)
            sent.append(file_id)
        return True

    monkeypatch.setattr(mada_file_cycle, 'check_protection', lambda config_path: None)
    monkeypatch.setattr(mada_file_cycle, 'run_file', fake_run_file)
    os.chdir(os.path.dirname(scaler.out_dir))
    mada_file_cycle.run_period('cfg', 7, 3, 10, [('B', '1.1.1.1')], {}, None, scaler)
    assert sent == [0, 1, 2] and scaler.pid is None
    assert count_lines(scaler.out_dir + '/per0007') == 3


def test_run_period_stops_when_scaler_misses_a_file(scaler, monkeypatch):
    import mada_file_cycle

    monkeypatch.setattr(mada_file_cycle, 'check_protection', lambda config_path: None)
    monkeypatch.setattr(mada_file_cycle, 'run_file', lambda *args, **kwargs: True)
    os.chdir(os.path.dirname(scaler.out_dir))
    with pytest.raises(ScalerError, match='did not record file 0'):
        mada_file_cycle.run_period('cfg', 8, 3, 10, [('B', '1.1.1.1')], {}, None, scaler)
    assert scaler.pid is not None


def test_remote_output_root(scaler, tmp_path):
    remote_root = tmp_path / 'remote_view'
    os.symlink(os.path.dirname(scaler.out_dir), remote_root)
    settings = {'ssh': scaler.ssh, 'command': scaler.command, 'output_root': os.path.dirname(scaler.out_dir),
                'remote_output_root': str(remote_root)}
    runner = ScalerRunner(settings, run='run2')
    assert runner.remote_out_dir == str(remote_root / 'run2') and runner.out_dir != runner.remote_out_dir
    runner.start(0)
    assert os.path.exists(runner.out_dir + '/per0000')
    runner.stop()
