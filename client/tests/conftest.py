import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.dirname(HERE)
HOME = tempfile.mkdtemp(prefix='mada_client_test_')
os.environ['MADAHOME'] = HOME
sys.path.insert(0, CLIENT_DIR)

TOKEN = 'test-token'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}


def make_home():
    shutil.rmtree(HOME, ignore_errors=True)
    for sub in ('scripts', 'run', 'data'):
        os.makedirs(f'{HOME}/{sub}')
    os.symlink(f'{CLIENT_DIR}/mada_client_simulator.py', f'{HOME}/scripts/mada.py')


def make_run(name, config=True, periods=1, files=2):
    run_dir = f'{HOME}/data/{name}'
    for p in range(periods):
        os.makedirs(f'{run_dir}/per{p:04d}')
        for n in range(files):
            for board in ('B1', 'B2'):
                runinfo = {'start': 100.0 + n, 'end': 101.0 + n, 'size': '2000'}
                if n == 1 and p == 0:
                    runinfo.update({'valid': False, 'invalid_reason': 'reader died'})
                with open(f'{run_dir}/per{p:04d}/{board}_{n:04d}.info', 'w') as f:
                    json.dump({'runinfo': runinfo}, f)
    if config:
        with open(f'{run_dir}/MADA_config.json', 'w') as f:
            json.dump({'gigaIwaki': {'B1': {'active': 1, 'IP': '1.1.1.1'}, 'B2': {'active': 1, 'IP': '1.1.1.2'}}}, f)
    return run_dir


@pytest.fixture
def client():
    make_home()
    from fastapi.testclient import TestClient
    import mada_client_files
    from mada_client_app import create_app
    from mada_client_config import Settings

    raw = {'listen_host': '127.0.0.1', 'port': 8765, 'allowed_servers': ['testclient'], 'data_root': f'{HOME}/data',
           'carry_over_config': True, 'defaults': {'file_num': 3, 'event_num': 1000},
           'limits': {'file_num_max': 100, 'event_num_max': 5000}}
    settings = Settings(raw, TOKEN)
    settings.simulate = True
    settings.sim_env = {'MADA_SIM_FILE_SEC': '0.6', 'MADA_SIM_SHUTDOWN_SEC': '0.5'}
    mada_client_files.clear_cache()
    yield TestClient(create_app(settings), headers=HEADERS), settings
    try:
        import mada_client_ops
        mada_client_ops.stop_daq('test')
    except Exception:
        pass
