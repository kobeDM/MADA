#!/usr/bin/env bash
# One-time installation of the daq-server: creates .venv, installs the
# dependencies and writes config/MADA_server.json (with a fresh session_secret).
# Safe to re-run; it never overwrites an existing config.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 8))' \
    || { echo "Python 3.8 or later is required (set PYTHON=/path/to/python3)." >&2; exit 1; }

if [ ! -d .venv ]; then
    echo "Creating .venv ..."
    "$PYTHON" -m venv .venv
fi
echo "Installing dependencies ..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r server/requirements.txt

CONFIG=config/MADA_server.json
if [ -e "$CONFIG" ]; then
    echo "$CONFIG already exists; leaving it as it is."
else
    .venv/bin/python - "$CONFIG" <<'PY'
import json, os, secrets, sys
with open('config/MADA_server_SKEL.json') as f:
    config = json.load(f)
home = os.path.expanduser('~')
config['session_secret'] = secrets.token_hex(32)
config['state_dir'] = os.path.join(home, 'mada_server', 'state')
config['client']['token_file'] = os.path.join(home, '.mada_server_client_token')
with open(sys.argv[1], 'w') as f:
    json.dump(config, f, indent=4)
    f.write('\n')
os.chmod(sys.argv[1], 0o600)
print(f'Wrote {sys.argv[1]}')
PY
fi

cat <<MSG

Next steps:
  1. Edit $HERE/$CONFIG: set client.base_url (and port, presets if needed).
  2. Put the daq-client token in the file named by client.token_file, mode 600:
       echo -n '<token>' > ~/.mada_server_client_token && chmod 600 ~/.mada_server_client_token
  3. source $HERE/setup.sh
  4. mada_server.py adduser <username> operator
  5. mada_server.py -d
MSG
