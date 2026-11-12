"""Where the MADA scripts and run files are. Imported first by every client
module: it puts the scripts directory on sys.path, so the client reuses the
MADA modules instead of duplicating them."""

import os
import sys

if 'MADAHOME' not in os.environ:
    raise RuntimeError('MADAHOME is not set; source setup.sh first')

MADAHOME = os.environ['MADAHOME']
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

RUN_DIR = MADAHOME + '/run'
MADA_PY = MADAHOME + '/scripts/mada.py'
CLIENT_STATE_PATH = RUN_DIR + '/mada_client.json'
CLIENT_LOG_PATH = RUN_DIR + '/mada_client.log'
VETO_STATE_PATH = RUN_DIR + '/veto.state'
