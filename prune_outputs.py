"""Keep only queued/rendered MP4 folders in the Actions cache.

The workflow uploads an artifact before pruning. Uploaded videos remain available
in their GitHub artifact; queued videos stay cached so they can be retried later.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path


def main() -> int:
    output = Path(os.getenv("OUTPUT_DIR", "output_videos"))
    db = Path(os.getenv("DATA_DIR", "data")) / "history.db"
    if not output.exists():
        print("No output directory; nothing to prune.")
        return 0
    if not db.exists():
        print("No history database; preserving output files.")
        return 0

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT folder, status FROM videos WHERE folder IS NOT NULL"
        ).fetchall()

    keep = {
        Path(folder).resolve()
        for folder, status in rows
        if status in ("queued", "rendered")
    }
    removed = 0
    for child in output.iterdir():
        if child.is_dir() and child.resolve() not in keep:
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
    print(f"Output cache cleanup complete: removed {removed} completed folder(s), "
          f"kept {len(keep)} queued/rendered folder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
