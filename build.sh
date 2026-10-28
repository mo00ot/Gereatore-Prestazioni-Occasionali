#!/bin/sh
# Crea l'app per macOS (dist/Ricevute.app) o Linux (dist/Ricevute).
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller
if [ "$(uname)" = "Darwin" ]; then MODO="--onedir"; else MODO="--onefile"; fi
.venv/bin/pyinstaller --noconfirm --clean --windowed $MODO --name Ricevute \
  --exclude-module pydoc --exclude-module numpy ricevute.py
echo "Fatto: guarda nella cartella dist/"
