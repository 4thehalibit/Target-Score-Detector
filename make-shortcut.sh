#!/usr/bin/env bash
# Install a desktop launcher ("Rinehart 18-1 Scorer") into the app menu.
# Safe to re-run; it just rewrites the entry with the current repo path.
set -euo pipefail

DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
chmod +x "$DIR/run.sh"

APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"
DESKTOP="$APPS/rinehart-scorer.desktop"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Rinehart 18-1 Scorer
Comment=Live camera scorer for the Rinehart 18-1 clover face
Exec=$DIR/run.sh
Icon=$DIR/icon.png
Terminal=false
Categories=Utility;Graphics;
EOF

chmod +x "$DESKTOP"
update-desktop-database "$APPS" 2>/dev/null || true

echo "Installed launcher: $DESKTOP"
echo "Search your apps for 'Rinehart 18-1 Scorer' (you can drag it to the dock)."
echo
echo "Tip: to see errors while testing, edit the file and set Terminal=true."
