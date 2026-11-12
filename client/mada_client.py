#!/usr/bin/env python3

"""The DAQ client: an HTTP API on the DAQ PC to start, stop and watch the DAQ.
--simulate runs it against a simulated DAQ in a temporary MADAHOME, with no
hardware."""

import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SIM_TOKEN = 'sim-token'


def arg_parser():
    parser = argparse.ArgumentParser(description='MADA DAQ client')
    parser.add_argument('-c', '--config', help='client settings (default: $MADAHOME/config/MADA_client.json)')
    parser.add_argument('--simulate', action='store_true', help='use a simulated DAQ in a temporary MADAHOME')
    parser.add_argument('--sim-home', help='directory for the simulation (default: a new temporary one)')
    parser.add_argument('--sim-file-sec', type=float, default=3.0, help='simulated seconds per file')
    parser.add_argument('--sim-fail-after', type=int, default=0, help='the simulated DAQ fails after this many files (0: never)')
    parser.add_argument('--sim-lag', action='store_true', help='the second simulated board lags behind')
    parser.add_argument('--sim-invalid-file', type=int, default=-1, help='file number that comes out invalid')
    parser.add_argument('--port', type=int, help='listen port')
    return parser.parse_args()


def prepare_simulation(args):
    """A MADAHOME with the simulator as scripts/mada.py, a data root with one run,
    and a token file. Returns the settings dict and the environment for the daemon."""
    home = os.path.abspath(args.sim_home or tempfile.mkdtemp(prefix='mada_sim_'))
    for sub in ('scripts', 'run', 'data/sim_run'):
        os.makedirs(f'{home}/{sub}', exist_ok=True)
    link = f'{home}/scripts/mada.py'
    if not os.path.islink(link):
        os.symlink(f'{HERE}/mada_client_simulator.py', link)

    boards = {f'SIM-{i}': {'active': 1, 'IP': f'192.168.100.{10 + i}', 'Vth': 9000, 'bias': 8000} for i in range(1, 3)}
    config = f'{home}/data/sim_run/MADA_config.json'
    if not os.path.exists(config):
        with open(config, 'w') as f:
            json.dump({'gigaIwaki': boards}, f, indent=4)
    token_file = f'{home}/token'
    with open(token_file, 'w') as f:
        f.write(SIM_TOKEN + '\n')
    os.chmod(token_file, 0o600)
    os.environ['MADAHOME'] = home
    print(f'Simulation: MADAHOME={home}, token={SIM_TOKEN}')
    return home


def main():
    args = arg_parser()
    if args.simulate:
        home = prepare_simulation(args)
    elif 'MADAHOME' not in os.environ:
        sys.exit('MADAHOME is not set; source setup.sh first')
    else:
        home = os.environ['MADAHOME']

    import uvicorn
    from mada_client_app import create_app
    from mada_client_config import ClientConfigError, Settings, load_settings

    try:
        if args.simulate:
            raw = {'listen_host': '127.0.0.1', 'port': 8765, 'carry_over_config': True,
                   'defaults': {'file_num': 5, 'event_num': 1000}, 'limits': {'file_num_max': 10000, 'event_num_max': 100000},
                   'allowed_servers': ['127.0.0.1'], 'data_root': f'{home}/data'}
            settings = Settings(raw, SIM_TOKEN)
            settings.simulate = True
            settings.sim_env = {'MADA_SIM_FILE_SEC': str(args.sim_file_sec), 'MADA_SIM_FAIL_AFTER': str(args.sim_fail_after),
                                'MADA_SIM_LAG': '1' if args.sim_lag else '0', 'MADA_SIM_INVALID_FILE': str(args.sim_invalid_file)}
        else:
            settings = load_settings(args.config or f'{home}/config/MADA_client.json')
    except ClientConfigError as e:
        sys.exit(f'Error: {e}')

    uvicorn.run(create_app(settings), host=settings.listen_host, port=args.port or settings.port)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main()
