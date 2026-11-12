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
    one_time_topic = os.getenv("DATA_DIR", "data")
    topic_file = os.path.join(one_time_topic, "next_topic.txt")
    if os.path.isfile(topic_file):
        with open(topic_file, encoding="utf-8") as f:
            requested_topic = f.read().strip()
        if requested_topic:
            command.extend(["--topic", requested_topic])
            print("One-time topic override loaded; it will be consumed only after a successful run.")
    print("Starting one Arabic Shorts cycle with visual relevance checks and channel-stat learning...")
    result = subprocess.call(command, env=os.environ.copy())
    if result == 0 and os.path.isfile(topic_file):
        os.remove(topic_file)
        print("One-time topic override consumed after successful run.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
