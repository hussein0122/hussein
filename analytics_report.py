"""Export the channel's last-28-day YouTube Analytics for the ShortsPilot learning loop."""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
METRICS = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,subscribersGained"


def main() -> int:
    required = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
    if any(not os.getenv(k, "").strip() for k in required):
        print("ERROR: YouTube OAuth secrets are missing.", file=sys.stderr)
        return 2

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"].strip(),
        client_secret=os.environ["YT_CLIENT_SECRET"].strip(),
        scopes=SCOPES,
    )
    try:
        creds.refresh(Request())
        api = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=27)
        response = api.reports().query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            dimensions="video",
            sort="-views",
            maxResults=200,
            metrics=METRICS,
        ).execute()
    except HttpError as exc:
        print(f"ERROR: YouTube Analytics report failed (HTTP {exc.resp.status}).", file=sys.stderr)
        print("The token may lack yt-analytics.readonly permission, or the API may not be enabled.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Could not retrieve YouTube Analytics ({type(exc).__name__}).", file=sys.stderr)
        return 1

    headers = response.get("columnHeaders", [])
    rows = [dict(zip((h["name"] for h in headers), row)) for row in response.get("rows", [])]
    out = Path(os.getenv("DATA_DIR", "data"))
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "metrics": METRICS.split(","),
        "rows": rows,
    }
    (out / "youtube_analytics_28d.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Analytics period: {start.isoformat()} to {end.isoformat()}")
    print(f"Videos with report data: {len(rows)}")
    for row in rows[:10]:
        print(
            "video={video} views={views} avg_view_pct={averageViewPercentage} "
            "avg_view_seconds={averageViewDuration} watch_minutes={estimatedMinutesWatched}".format(
                **{k: row.get(k, "-") for k in (
                    "video", "views", "averageViewPercentage", "averageViewDuration", "estimatedMinutesWatched"
                )}
            )
        )
    if not rows:
        print("No Analytics rows yet; this is normal for a new channel or videos without reportable data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
