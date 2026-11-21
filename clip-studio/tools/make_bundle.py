#!/usr/bin/env python3
"""Builds dist/clip-studio-bundle.py: ONE self-extracting file containing the whole app.
Regenerate after changing any source file:  python3 tools/make_bundle.py"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["server.py", "engines.py", "openfilm_export.py", "web/index.html", "run.sh", "run.bat", "README.md",
         "requirements-optional.txt", ".gitignore", "tests/test_pipeline.py"]

TEMPLATE = '''#!/usr/bin/env python3
"""Clip Studio - single-file bundle.

    python3 clip-studio-bundle.py            extract into ./clip-studio and start the studio
    python3 clip-studio-bundle.py --no-run   extract only
    options: --dir PATH   --port N

Extracts code files only (your data/ folder is never touched). Needs Python 3.9+ and ffmpeg 5+.
This file is just a packaged copy; readable source lives in the repo under clip-studio/.
"""
import argparse
import base64
import os
import subprocess
import sys
from pathlib import Path

FILES = {
__FILES__
}


def main():
    ap = argparse.ArgumentParser(description="Clip Studio bundle")
    ap.add_argument("--dir", default="clip-studio")
    ap.add_argument("--port", type=int, default=8369)
    ap.add_argument("--no-run", action="store_true")
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    for rel, b64 in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(b64))
        if rel == "run.sh":
            p.chmod(0o755)
    print(f"Clip Studio extracted to {root}")
    if a.no_run:
        return
    print(f"Starting on http://127.0.0.1:{a.port}  (Ctrl+C to stop)")
    try:
        subprocess.call([sys.executable, str(root / "server.py")], env=dict(os.environ, PORT=str(a.port)))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
'''

blocks = []
for rel in FILES:
    b64 = base64.b64encode((ROOT / rel).read_bytes()).decode()
    lines = "\n".join(f'        "{b64[i:i + 96]}"' for i in range(0, len(b64), 96))
    blocks.append(f'    "{rel}": (\n{lines}\n    ),')
out = ROOT / "dist" / "clip-studio-bundle.py"
out.write_text(TEMPLATE.replace("__FILES__", "\n".join(blocks)), encoding="utf-8")
out.chmod(0o755)
print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(FILES)} files)")
