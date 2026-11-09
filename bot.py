"""Run one Arabic Short using the upstream PurffleShorts engine."""
from __future__ import annotations
import os
import shutil
import subprocess
import sys

def main() -> int:
    executable = shutil.which("purffle-shorts")
    if not executable:
        print("ERROR: purffle-shorts CLI is not installed.", file=sys.stderr)
        return 2
    # Explicitly one video per invocation: scheduler triggers this three times daily.
    command = [executable, "run", "--once", "--count", "1"]
    print("Starting one Shorts generation cycle...")
    return subprocess.call(command, env=os.environ.copy())

if __name__ == "__main__":
    raise SystemExit(main())
