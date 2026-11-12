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

    # The workflow explicitly controls privacy and daily limits; these are local-run fallbacks.
    os.environ.setdefault("LEARN_FROM_STATS", "true")
    os.environ.setdefault("YT_PRIVACY", "public")
    os.environ.setdefault("YT_DAILY_LIMIT", "3")
    os.environ.setdefault("TIMEZONE", "Africa/Cairo")

    command = [executable, "run", "--once", "--count", "1"]
    print("Starting one Arabic Shorts cycle with visual relevance checks and channel-stat learning...")
    return subprocess.call(command, env=os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main())
