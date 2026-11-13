#!/bin/bash
# The 48 - AI's Best Mate: one-command deploy on a fresh Linux box.
#
#   bash deploy.sh            install and start on port 8048
#   PORT=9000 bash deploy.sh  use another port
#
# What it does: checks Python, runs the tests, creates a sign-in password on this box (never in
# the repo), and starts the app - as a systemd service when run as root on a systemd machine,
# otherwise as a background process from this folder.
# What it never does: touch DNS, domains, Caddy, or any other service. It only ever starts,
# restarts or replaces its own "best-mate" service. Putting it behind a public address is a
# separate, deliberate step: the Caddy lines are printed at the end for you to add yourself.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
PORT="${PORT:-8048}"

echo "== 1. Python =="
python3 -c 'import sys; assert sys.version_info >= (3, 8), "Python 3.8 or newer is needed"; print("python", sys.version.split()[0])'

echo "== 2. Tests (money maths, fabrication check, end to end) =="
python3 -m unittest discover -s tests 2>&1 | tail -4

mkdir -p data
new_env() {   # $1 = file to create with a fresh password and session secret
  python3 - "$1" "$PORT" <<'PY'
import os, secrets, sys
path, port = sys.argv[1], sys.argv[2]
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as fh:
    fh.write("APP_PASSWORD=%s\nSESSION_SECRET=%s\nHOST=127.0.0.1\nPORT=%s\n" % (
        secrets.token_urlsafe(12), secrets.token_hex(32), port))
PY
}

echo "== 3. Start =="
if [ "$(id -u)" = "0" ] && [ -d /run/systemd/system ]; then
  ENV_FILE=/etc/best-mate.env
  [ -f "$ENV_FILE" ] || { new_env "$ENV_FILE"; FRESH=1; }
  OWNER="$(stat -c %U "$HERE")"
  cat > /etc/systemd/system/best-mate.service <<UNIT
[Unit]
Description=The 48 - AI's Best Mate (quoting app)
After=network.target

[Service]
User=$OWNER
WorkingDirectory=$HERE
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/env python3 $HERE/server.py
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable best-mate >/dev/null 2>&1
  systemctl restart best-mate
  HOW="systemd service 'best-mate'  (logs: journalctl -u best-mate)"
else
  ENV_FILE="$HERE/data/.env"
  [ -f "$ENV_FILE" ] || { new_env "$ENV_FILE"; FRESH=1; }
  if [ -f data/server.pid ] && kill -0 "$(cat data/server.pid)" 2>/dev/null; then
    kill "$(cat data/server.pid)"; sleep 1          # only ever our own earlier process
  fi
  set -a; . "$ENV_FILE"; set +a
  nohup python3 "$HERE/server.py" > data/server.log 2>&1 &
  echo $! > data/server.pid
  HOW="background process $(cat data/server.pid)  (logs: $HERE/data/server.log, stop: kill \$(cat $HERE/data/server.pid))"
fi

PORT_NOW="$(grep '^PORT=' "$ENV_FILE" | cut -d= -f2)"
for _ in $(seq 1 20); do
  if python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$PORT_NOW/api/health', timeout=2)" 2>/dev/null; then UP=1; break; fi
  sleep 0.5
done
[ "${UP:-}" = "1" ] || { echo "The app did not come up on port $PORT_NOW. Is something else using it? Check the logs."; exit 1; }

echo
echo "== APP UP =="
echo "Open on this box:  http://127.0.0.1:$PORT_NOW/"
echo "Running as:        $HOW"
if [ "${FRESH:-}" = "1" ]; then
  echo "Sign-in password:  $(grep '^APP_PASSWORD=' "$ENV_FILE" | cut -d= -f2)   (shown once; stored in $ENV_FILE)"
else
  echo "Sign-in password:  unchanged, in $ENV_FILE"
fi
echo "Jane's voice and the AI model are optional: add VOICE_BASE_URL / LLM_BASE_URL (and keys) to $ENV_FILE and run this again."
echo
echo "To reach it from a phone it needs HTTPS (the offline mode and the microphone both require it)."
echo "When you are ready, add this to your Caddyfile yourself - this script does not touch Caddy or DNS:"
echo
echo "    quotes.example.com {"
echo "        reverse_proxy 127.0.0.1:$PORT_NOW"
echo "    }"
