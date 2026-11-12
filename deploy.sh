#!/bin/bash
# AI9 Week 1 harness - one-command setup + proof on any box (Mac or Linux).
# No keys, no network, no pip. Copies nothing outside this directory.
#
# Usage:
#   1. scp -r ai9-validation root@<box>:/opt/
#   2. ssh root@<box> 'bash /opt/ai9-validation/deploy.sh'
set -euo pipefail

cd "$(dirname "$0")"

echo "=== 1. python check ==="
python3 --version

echo "=== 2. config ==="
if [ ! -f config.json ]; then
    cp config.example.json config.json
    echo "config.json created (offline stub, \$0)"
else
    echo "config.json exists - keeping it"
fi

echo "=== 3. task pack integrity ==="
python3 taskpack/gen.py

echo "=== 4. smoke test (full end-to-end proof) ==="
python3 tests/smoke_test.py

echo ""
echo "=== DEPLOYED AND VERIFIED ==="
echo "Smoke report:  $(pwd)/results-smoke/report.md"
echo "Smoke scores:  $(pwd)/results-smoke/scores.json"
echo "Real runs go to: $(pwd)/results/results.db (the smoke test never touches it)"
echo "Console:  python3 organism.py connect --lan"
echo ""
echo "Next: point config.json at a real model (see README), tune on the"
echo "dev pack only, then run the frozen pack once with --i-know-frozen."
