#!/usr/bin/env bash
# Target Score Detector -- installer for Debian / Ubuntu / Pop!_OS.
# Creates a local Python virtualenv and installs OpenCV + NumPy into it.
set -euo pipefail

cd "$(dirname "$0")"

echo ">> Installing system prerequisites (needs sudo)..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

echo ">> Creating virtualenv in ./.venv ..."
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo ">> Installing desktop launcher ..."
./make-shortcut.sh || echo "   (skipped shortcut; not a desktop session)"

cat <<'EOF'

Done. Launch the live scorer either way:

  * Tap "Rinehart 18-1 Scorer" in your apps menu (drag it to the dock), or
  * ./run.sh

Other tools:
  source .venv/bin/activate
  python clover_scorer.py path/to/photo.jpg out.png   # score one still photo
  python Driver.py                                      # original archery video demo

EOF
