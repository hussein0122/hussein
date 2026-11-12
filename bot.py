"""Run exactly one Arabic Short using the pinned PurffleShorts engine."""
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

    # Keep the first production verification deliberately safe.
    os.environ.setdefault("LEARN_FROM_STATS", "true")
    os.environ.setdefault("YT_PRIVACY", "private")
    os.environ.setdefault("YT_DAILY_LIMIT", "1")
    os.environ.setdefault("TIMEZONE", "Africa/Cairo")

    command = [executable, "run", "--once", "--count", "1"]
    print("Starting one Shorts generation cycle with channel-stat learning enabled...")
    return subprocess.call(command, env=os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main())
