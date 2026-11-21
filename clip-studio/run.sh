#!/usr/bin/env bash
# One-click launcher for macOS / Linux.   ./run.sh            start the studio
#                                         ./run.sh --install  also create .venv and install optional extras
cd "$(dirname "$0")" || exit 1
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. Install it first:  brew install ffmpeg   |   sudo apt install ffmpeg"; exit 1
fi
PY=python3
if [ "$1" = "--install" ]; then
  $PY -m venv .venv && . .venv/bin/activate && pip install -r requirements-optional.txt || exit 1
fi
[ -d .venv ] && . .venv/bin/activate && PY=python
PORT="${PORT:-8369}"
( sleep 1.5; (command -v open >/dev/null && open "http://127.0.0.1:$PORT") || (command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:$PORT") ) >/dev/null 2>&1 &
PORT="$PORT" exec $PY server.py
