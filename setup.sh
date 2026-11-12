#!/usr/bin/env bash
# Source this (do not execute it) to use the daq-server commands from any
# directory:  source /path/to/MADA/setup.sh
# Activates .venv, adds server/ to PATH and sets MADA_SERVER_HOME and
# MADA_SERVER_CONFIG (the default config for mada_server.py).

_mada_server_home="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$_mada_server_home/.venv/bin/activate" ]; then
    echo "setup.sh: .venv not found; run $_mada_server_home/install.sh first." >&2
    return 1 2>/dev/null || exit 1
fi

export MADA_SERVER_HOME="$_mada_server_home"
export MADA_SERVER_CONFIG="${MADA_SERVER_CONFIG:-$MADA_SERVER_HOME/config/MADA_server.json}"
# shellcheck disable=SC1091
source "$MADA_SERVER_HOME/.venv/bin/activate"
case ":$PATH:" in
    *":$MADA_SERVER_HOME/server:"*) ;;
    *) export PATH="$MADA_SERVER_HOME/server:$PATH" ;;
esac
unset _mada_server_home
