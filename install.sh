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

cat <<'EOF'

Done. To use it:

  source .venv/bin/activate

  # Score a single straight-on photo of the Rinehart 18-1 clover face:
  python clover_scorer.py path/to/your_photo.jpg out.png

  # Original archery video demo (annotates res/input/video.mp4):
  python Driver.py

EOF
