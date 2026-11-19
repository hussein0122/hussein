"""Select exactly one seasonal GitHub cron for each Cairo publishing slot.

GitHub scheduled runs can start late. Match the cron expression that fired to
Cairo's current UTC offset instead of rejecting a valid run based on runner
start time. The paired summer/winter crons are mutually exclusive by offset.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

SCHEDULES_BY_UTC_OFFSET_MINUTES = {
    120: {
        "5 8 * * *": "10:05",
        "5 14 * * *": "16:05",
        "5 20 * * *": "22:05",
    },
    180: {
        "5 7 * * *": "10:05",
        "5 13 * * *": "16:05",
        "5 19 * * *": "22:05",
    },
}


def evaluate_slot(event_name: str, schedule: str, utc_offset_minutes: int) -> tuple[bool, str]:
    """Return whether this event is the active seasonal cron and its Cairo slot."""
    if event_name != "schedule":
        return True, "manual"

    slot = SCHEDULES_BY_UTC_OFFSET_MINUTES.get(utc_offset_minutes, {}).get(schedule)
    if slot is None:
        return False, "inactive-season-or-unknown-cron"
    return True, slot


def main() -> None:
    now = datetime.now(ZoneInfo("Africa/Cairo"))
    offset_minutes = int(now.utcoffset().total_seconds() // 60)
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    schedule = os.environ.get("GITHUB_EVENT_SCHEDULE", "").strip()
    should_run, slot = evaluate_slot(event_name, schedule, offset_minutes)

    result = "PASS" if should_run else "SKIP"
    print(
        f"SLOT_CHECK={result} event={event_name} schedule={schedule or 'none'} "
        f"cairo_time={now.isoformat()} utc_offset_minutes={offset_minutes} slot={slot}"
    )
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"should_run={'true' if should_run else 'false'}\n")


if __name__ == "__main__":
    main()
