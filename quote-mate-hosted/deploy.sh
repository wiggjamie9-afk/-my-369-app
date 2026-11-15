#!/bin/bash
# Quote Mate (hosted): one-command deploy on a Linux box.
#
#   bash deploy.sh
#   PORT=9000 PUBLIC_URL=https://quotes.example.com bash deploy.sh
#
# It checks Python, runs the tests, makes an owner password for this box (never kept in the repo),
# and starts the server: as a systemd service when run as root on a systemd machine, otherwise as a
# background process from this folder. Run it again any time to restart; your data is untouched.
# It never touches DNS, Caddy or any other service. The Caddy lines to add are printed at the end.
# The folder ../roof-quote-mate must sit next to this one (it is the quote page itself).
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
PORT="${PORT:-8090}"

echo "== 1. Check =="
python3 -c 'import sys; assert sys.version_info >= (3, 8), "Python 3.8 or newer is needed"; print("python", sys.version.split()[0])'
[ -f ../roof-quote-mate/index.html ] || { echo "Can't find ../roof-quote-mate (the quote page). Put both folders side by side."; exit 1; }

echo "== 2. Tests =="
python3 -m unittest discover -s tests 2>&1 | tail -3

mkdir -p data
new_env() {   # $1 = file to create
  python3 - "$1" "$PORT" "${PUBLIC_URL:-}" <<'PY'
import os, secrets, sys
path, port, public = sys.argv[1], sys.argv[2], sys.argv[3]
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as fh:
    fh.write("ADMIN_PASSWORD=%s\nHOST=127.0.0.1\nPORT=%s\nTRUST_PROXY=1\n" % (secrets.token_urlsafe(14), port))
    if public:
        fh.write("PUBLIC_URL=%s\n" % public)
    fh.write("# To email leads to your customers, fill these in and run deploy.sh again:\n"
             "#SMTP_HOST=\n#SMTP_PORT=587\n#SMTP_USER=\n#SMTP_PASSWORD=\n#SMTP_FROM=\n")
PY
}

echo "== 3. Start =="
if [ "$(id -u)" = "0" ] && [ -d /run/systemd/system ]; then
  ENV_FILE=/etc/quote-mate.env
  [ -f "$ENV_FILE" ] || { new_env "$ENV_FILE"; FRESH=1; }
  OWNER="$(stat -c %U "$HERE")"
  cat > /etc/systemd/system/quote-mate.service <<UNIT
[Unit]
Description=Quote Mate (hosted)
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
  systemctl enable quote-mate >/dev/null 2>&1
  systemctl restart quote-mate
  HOW="systemd service 'quote-mate'  (logs: journalctl -u quote-mate)"
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
  if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT_NOW/healthz', timeout=2)" 2>/dev/null; then UP=1; break; fi
  sleep 0.5
done
[ "${UP:-}" = "1" ] || { echo "It did not come up on port $PORT_NOW. Is something else using it? Check the logs."; exit 1; }

echo
echo "== UP =="
echo "Sales page:     http://127.0.0.1:$PORT_NOW/"
echo "Owner console:  http://127.0.0.1:$PORT_NOW/admin"
echo "Running as:     $HOW"
if [ "${FRESH:-}" = "1" ]; then
  echo "Owner password: $(grep '^ADMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2)   (shown once; kept in $ENV_FILE)"
else
  echo "Owner password: unchanged, in $ENV_FILE"
fi
echo
echo "To put it on the internet, add this to your Caddyfile yourself (this script does not touch Caddy or DNS):"
echo
echo "    quotes.example.com {"
echo "        reverse_proxy 127.0.0.1:$PORT_NOW"
echo "    }"
echo
echo "Then run:  PUBLIC_URL=https://quotes.example.com bash deploy.sh   so lead emails link to the right address."
