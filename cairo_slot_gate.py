"""Select one active seasonal cron only while its Cairo slot is current.

GitHub may delay scheduled workflows for hours. Never publish a stale slot:
allow a small early-start tolerance and a bounded 30-minute late window.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
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
LATE_GRACE_MINUTES = 30
EARLY_TOLERANCE_MINUTES = 5


def evaluate_slot(
    event_name: str,
    schedule: str,
    now: datetime | None = None,
    grace_minutes: int = LATE_GRACE_MINUTES,
    early_tolerance_minutes: int = EARLY_TOLERANCE_MINUTES,
) -> tuple[bool, str]:
    """Return whether the event is the active seasonal cron and still on time."""
    if event_name != "schedule":
        return True, "manual"

    now = now or datetime.now(ZoneInfo("Africa/Cairo"))
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Cairo slot evaluation requires a timezone-aware datetime")

    offset_minutes = int(now.utcoffset().total_seconds() // 60)
    slot = SCHEDULES_BY_UTC_OFFSET_MINUTES.get(offset_minutes, {}).get(schedule)
    if slot is None:
        return False, "inactive-season-or-unknown-cron"

    hour, minute = (int(part) for part in slot.split(":"))
    today_slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    yesterday_slot = today_slot - timedelta(days=1)
    expected = min(
        (today_slot, yesterday_slot),
        key=lambda candidate: abs((now - candidate).total_seconds()),
    )
    delta_minutes = (now - expected).total_seconds() / 60

    if delta_minutes < -early_tolerance_minutes:
        return False, f"too-early:{slot}:early-by={abs(delta_minutes):.1f}m"
    if delta_minutes > grace_minutes:
        return False, f"expired:{slot}:late-by={delta_minutes:.1f}m"
    return True, slot


def main() -> None:
    now = datetime.now(ZoneInfo("Africa/Cairo"))
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    schedule = os.environ.get("GITHUB_EVENT_SCHEDULE", "").strip()
    should_run, slot = evaluate_slot(event_name, schedule, now)

    result = "PASS" if should_run else "SKIP"
    print(
        f"SLOT_CHECK={result} event={event_name} schedule={schedule or 'none'} "
        f"cairo_time={now.isoformat()} utc_offset_minutes="
        f"{int(now.utcoffset().total_seconds() // 60)} slot={slot}"
    )
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"should_run={'true' if should_run else 'false'}\n")


if __name__ == "__main__":
    main()
