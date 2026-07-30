#!/usr/bin/env bash
# Install desktop launchers for the scorer into the app menu.
# Creates two entries:
#   "Rinehart 18-1 Scorer"          -> normal, no terminal
#   "Rinehart 18-1 Scorer (Debug)"  -> opens a terminal so you can see errors
# Safe to re-run; it rewrites the entries with the current repo path.
set -euo pipefail

DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
chmod +x "$DIR/run.sh"

APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"

write_entry() {   # $1=file  $2=name  $3=terminal(true/false)
    local f="$APPS/$1"
    cat > "$f" <<EOF
[Desktop Entry]
Type=Application
Name=$2
Comment=Live camera scorer for the Rinehart 18-1 clover face
Exec=$DIR/run.sh
Icon=$DIR/icon.png
Terminal=$3
Categories=Utility;Graphics;
EOF
    chmod +x "$f"
    gio set "$f" metadata::trusted true 2>/dev/null || true
}

write_entry "rinehart-scorer.desktop"       "Rinehart 18-1 Scorer"         false
write_entry "rinehart-scorer-debug.desktop" "Rinehart 18-1 Scorer (Debug)" true

update-desktop-database "$APPS" 2>/dev/null || true

echo "Installed launchers in: $APPS"
echo "  * 'Rinehart 18-1 Scorer'          (normal)"
echo "  * 'Rinehart 18-1 Scorer (Debug)'  (opens a terminal to show errors)"
echo "Repo path baked into the launchers: $DIR"
