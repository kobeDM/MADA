#!/usr/bin/env python3

"""Entry point for the daq-server daemon (docs/specs/2026-11-12_3.md).

Usage:
  mada_server.py [-c config] [-d]            start the server (foreground, or
                                              background with -d, like mada.py -d)
  mada_server.py [-c config] stop            stop a backgrounded server
  mada_server.py [-c config] adduser <username> <role>
  mada_server.py [-c config] passwd <username>
  mada_server.py [-c config] rmuser <username>
  mada_server.py [-c config] listusers
"""

import argparse
import getpass
import os
import signal
import sys

import uvicorn

import mada_server_config as cfg
import mada_server_db as db
from mada_server_app import create_app

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    'config', 'MADA_server.json')


def _daemonize(log_file, pidfile_path):
    """Fork into the background and redirect stdout/stderr to log_file (the
    classic double-fork-free daemonize: fork, setsid in the child, parent exits)."""
    pid = os.fork()
    if pid > 0:
        with open(pidfile_path, 'w') as f:
            f.write(str(pid))
        print(f'Started in background (PID {pid}). Log: {log_file}')
        os._exit(0)

    os.setsid()
    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull_fd, sys.stdin.fileno())
    os.close(devnull_fd)

    sys.stdout.flush()
    sys.stderr.flush()
    log_fd = os.open(log_file, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)


def _install_sigterm_handler():
    def _handle(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _handle)


def cmd_serve(config, args):
    db.init_db(cfg.db_path(config))
    if args.daemon:
        _daemonize(cfg.log_path(config), cfg.pidfile_path(config))
    _install_sigterm_handler()

    app = create_app(config)
    try:
        uvicorn.run(app, host=config['listen_host'], port=config['port'])
    except KeyboardInterrupt:
        pass
    finally:
        if args.daemon:
            try:
                os.remove(cfg.pidfile_path(config))
            except FileNotFoundError:
                pass


def cmd_stop(config, args):
    pidfile_path = cfg.pidfile_path(config)
    try:
        with open(pidfile_path, 'r') as f:
            pid = int(f.read().strip())
    except FileNotFoundError:
        print('not running (no pidfile)')
        return
    try:
        os.kill(pid, signal.SIGTERM)
        print(f'sent SIGTERM to PID {pid}')
    except ProcessLookupError:
        print('pidfile is stale; removing it')
        os.remove(pidfile_path)


def _read_new_password():
    password = getpass.getpass('password: ')
    if password != getpass.getpass('confirm: '):
        sys.exit('passwords do not match')
    return password


def cmd_adduser(config, args):
    try:
        cfg.add_user(args.config, args.username, _read_new_password(), args.role)
    except cfg.ConfigError as e:
        sys.exit(str(e))
    print(f"created user '{args.username}' ({args.role}). Restart the server to apply.")


def cmd_passwd(config, args):
    try:
        cfg.set_password(args.config, args.username, _read_new_password())
    except cfg.ConfigError as e:
        sys.exit(str(e))
    print(f"password updated for '{args.username}'. Restart the server to apply.")


def cmd_rmuser(config, args):
    try:
        cfg.remove_user(args.config, args.username)
    except cfg.ConfigError as e:
        sys.exit(str(e))
    print(f"deleted user '{args.username}'. Restart the server to apply.")


def cmd_listusers(config, args):
    for username, entry in config.get('users', {}).items():
        print(f"{username}\t{entry['role']}")


def main():
    parser = argparse.ArgumentParser(description='MADA daq-server')
    parser.add_argument('-c', '--config', default=DEFAULT_CONFIG_PATH)
    parser.add_argument('-d', '--daemon', action='store_true',
                         help='detach from the terminal and run in the background')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('stop', help='stop a backgrounded server')

    adduser_parser = sub.add_parser('adduser', help='create a login user')
    adduser_parser.add_argument('username')
    adduser_parser.add_argument('role', choices=['viewer', 'operator'])

    passwd_parser = sub.add_parser('passwd', help="change a user's password")
    passwd_parser.add_argument('username')

    rmuser_parser = sub.add_parser('rmuser', help='delete a login user')
    rmuser_parser.add_argument('username')

    sub.add_parser('listusers', help='list login users')

    args = parser.parse_args()
    try:
        config = cfg.load_config(args.config)
    except cfg.ConfigError as e:
        sys.exit(str(e))

    handlers = {
        None: cmd_serve,
        'stop': cmd_stop,
        'adduser': cmd_adduser,
        'passwd': cmd_passwd,
        'rmuser': cmd_rmuser,
        'listusers': cmd_listusers,
    }
    handlers[args.command](config, args)


if __name__ == '__main__':
    main()
