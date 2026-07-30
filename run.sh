#!/usr/bin/env bash
# Launch the live scorer using this repo's virtualenv, from anywhere.
cd "$(dirname "$(readlink -f "$0")")"
exec ./.venv/bin/python live.py "$@"
