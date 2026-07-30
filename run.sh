#!/usr/bin/env bash
# Launch the live scorer from anywhere. Prefers this repo's virtualenv,
# falls back to system Python. Logs errors so a failed launch isn't silent.
cd "$(dirname "$(readlink -f "$0")")"

LOG="$PWD/last-run.log"

if [ -x ./.venv/bin/python ]; then
    PY=./.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

# Run, capturing output. If it exits non-zero, surface the reason.
if ! "$PY" live.py "$@" >"$LOG" 2>&1; then
    MSG="Rinehart scorer failed to start. See $LOG"
    command -v notify-send >/dev/null 2>&1 && \
        notify-send "Rinehart 18-1 Scorer" "$MSG"
    echo "$MSG" >&2
    tail -n 20 "$LOG" >&2
    exit 1
fi
