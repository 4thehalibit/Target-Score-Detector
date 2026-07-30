#!/usr/bin/env bash
# Launch the live scorer from anywhere. Picks the first Python that actually
# has OpenCV (repo venv, then system python3/python). Logs errors so a failed
# launch isn't silent.
cd "$(dirname "$(readlink -f "$0")")"

LOG="$PWD/last-run.log"

pick_py() {
    for c in "./.venv/bin/python" python3 python; do
        if { [ -x "$c" ] || command -v "$c" >/dev/null 2>&1; } \
           && "$c" -c "import cv2" >/dev/null 2>&1; then
            echo "$c"; return 0
        fi
    done
    return 1
}

PY="$(pick_py || true)"
if [ -z "$PY" ]; then
    MSG="No Python with OpenCV found. Run ./install.sh, or: pip install opencv-python numpy"
    command -v notify-send >/dev/null 2>&1 && notify-send "Rinehart 18-1 Scorer" "$MSG"
    echo "$MSG" | tee "$LOG" >&2
    exit 1
fi

if ! "$PY" live.py "$@" >"$LOG" 2>&1; then
    MSG="Rinehart scorer failed to start. See $LOG"
    command -v notify-send >/dev/null 2>&1 && notify-send "Rinehart 18-1 Scorer" "$MSG"
    echo "$MSG" >&2
    tail -n 20 "$LOG" >&2
    exit 1
fi
