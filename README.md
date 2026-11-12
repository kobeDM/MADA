# MADA daq-server

A web server that runs on a separate PC. It calls the HTTP API of daq-client (on the DAQ PC) so the DAQ can be monitored, started and stopped from a browser.
This branch (`dev-cn1-daq-server`) contains the daq-server only; the DAQ itself (`scripts/`, `source/`, etc.) is not included (see `main`).

- If the server goes down, the DAQ and data taking keep running.
- The server never touches the boards or the data files (`.mada`); it only uses the daq-client API.
- API contract and specifications: [docs/specs/INDEX.md](docs/specs/INDEX.md)

## Features

| Page / feature | Description |
|---|---|
| Dashboard (`/`) | Connection state, phase (`idle` / `starting` / `running` / `stopping`), run / period / file number, per-board progress (lagging boards highlighted), protection (LV auto-reset monitor, veto), last exit, notifications. Updated live over SSE |
| Start / stop | Operators only. Start takes run, `file_num`, `event_num`, SCI, `config_from` and a source preset, with a confirmation dialog. There is no force-kill |
| Runs (`/runs`) | List of runs and periods. Links to each period's files and warnings, and to the run's `MADA_config.json` (read-only) |
| Files | Valid / invalid (with reason), start and end time, size per board |
| Warnings | Records of `warnings.log`, filterable by level and source |
| Log (`/log`) | Tail of the DAQ daemon log (every 2 s) |
| History (`/history`) | Append-only history of start / stop operations, and the notification history |
| Notifications | DAQ abnormal exit, period completed / ended by a stop, connection lost / restored, protection failure, invalid file, stalled progress. Shown on screen and kept in the DB; nothing is sent externally |
| Authentication | Only logged-in users can view. Roles: `viewer` (view only) and `operator` (can also start, stop and acknowledge notifications). Start, stop and acknowledge are CSRF-protected |

The server polls daq-client whether or not a browser is connected (`/status` every 2 s, `/progress` every 1 s, warnings every 5 s, files every 10 s).
After 3 consecutive failures it reports the connection as lost and retries with exponential backoff (2 s up to 30 s). While disconnected, the phase is shown as `Unknown`.

## Setup

Requirements: Python 3.8 or later, and network access to the DAQ PC where daq-client runs.

### Quick start

```bash
git clone git@github.com:kobeDM/MADA.git
cd MADA
git checkout dev-cn1-daq-server

./install.sh                 # creates .venv, installs dependencies, writes config/MADA_server.json
# edit config/MADA_server.json (at least client.base_url), then create the token file (step 2 below)
source setup.sh              # activates .venv, adds server/ to PATH, sets the env variables
mada_server.py adduser <username> operator
mada_server.py -d
```

`install.sh` is safe to re-run: it reuses `.venv` and never overwrites an existing config. Set `PYTHON=/path/to/python3` to choose the interpreter.

`source setup.sh` (run it in every new shell, or add it to `~/.bashrc`) does the following, so the commands work from any directory:

| What | Value |
|---|---|
| `MADA_SERVER_HOME` | The repository directory |
| `MADA_SERVER_CONFIG` | Default config file for `mada_server.py` (`$MADA_SERVER_HOME/config/MADA_server.json`; set it beforehand to use another file) |
| `PATH` | `server/` is added, so `mada_server.py` can be run directly |
| virtualenv | `.venv` is activated |

### 1. Config file

`install.sh` writes `config/MADA_server.json` from `config/MADA_server_SKEL.json`, with a freshly generated `session_secret`, `state_dir` under `~/mada_server/state`, and `client.token_file` set to `~/.mada_server_client_token`. The file is in `.gitignore` (do not commit it) and has mode 600. Edit it:

| Key | Description |
|---|---|
| `listen_host`, `port` | Listen address and port (default `0.0.0.0`, `8080`) |
| `cookie_secure` | `true` behind an HTTPS reverse proxy, `false` for plain HTTP |
| `state_dir` | Where the server keeps its state (DB `mada_server.db`, `mada_server.pid`, `mada_server.log`). Created if missing |
| `session_secret` | Signing key of the session cookie. Required. Keep it secret |
| `users` | Login users. Manage them with the commands below instead of editing by hand |
| `client.base_url` | URL of daq-client (e.g. `http://192.168.100.10:8765`) |
| `client.token_file` | The token file from step 2 |
| `client.timeout` | Timeout of requests to daq-client [s] (default 5.0) |
| `presets` | Source presets on the start form (`name` and `event_num`) |

If the config has problems, the server lists all of them and exits at startup.

### 2. Token for daq-client

Create a file containing the daq-client token on a single line, and set its permission to 600 (the server refuses to start otherwise).

```bash
echo -n '<daq-client token>' > ~/.mada_server_client_token
chmod 600 ~/.mada_server_client_token
```

### 3. Users

Users are managed from the CLI only (they cannot be created over HTTP). Passwords are hashed with bcrypt and stored in the config file.

```bash
mada_server.py adduser <username> operator   # or viewer
mada_server.py passwd <username>
mada_server.py rmuser <username>
mada_server.py listusers
```

Adding, changing or removing a user takes effect after the server is restarted.

To use another config file, put `-c <path>` before the subcommand (this overrides `MADA_SERVER_CONFIG`).

### Manual installation

Without the scripts: `python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt`, copy `config/MADA_server_SKEL.json` to `config/MADA_server.json`, put a random value (`python3 -c "import secrets; print(secrets.token_hex(32))"`) in `session_secret`, and run `python3 server/mada_server.py -c <config>`.

## Starting the server

```bash
# Foreground (stop with Ctrl+C)
mada_server.py

# Background (daemon)
mada_server.py -d
```

Then open `http://<server host>:<port>/` in a browser and log in.

With `-d`, the PID is written to `<state_dir>/mada_server.pid` and stdout / stderr go to `<state_dir>/mada_server.log`.

## Stopping the server

```bash
# Daemonized server
mada_server.py stop

# Foreground server: Ctrl+C
```

`stop` sends SIGTERM to the PID in the pidfile (the server removes the pidfile on exit). If only a stale pidfile is left, it is removed.
Stopping the server does not stop the DAQ. To stop the DAQ, use the stop button on the dashboard (or daq-client).

## Tests

```bash
python3 -m unittest discover -s server/tests -t server
```

These check the poller's notification logic against a fake daq-client. You can also run the daq-client simulator (`client/mada_client.py --simulate` on the `dev-cn1-daq-client` branch) and point the server at it for an end-to-end check.

## Layout

```
server/
  mada_server.py          start, daemonize, stop, user management
  mada_server_app.py      FastAPI app, pages and APIs
  mada_server_auth.py     login, roles, CSRF
  mada_server_client.py   HTTP client of daq-client
  mada_server_poller.py   periodic polling of daq-client and notifications
  mada_server_state.py    in-memory latest state and SSE fan-out
  mada_server_db.py       SQLite (operation history, notifications, cursors)
  mada_server_config.py   config loading, validation, user management
  templates/, static/     pages
  tests/                  unit tests
install.sh, setup.sh            installation and shell environment
config/MADA_server_SKEL.json   config template
docs/specs/                    API contract and specifications
```
