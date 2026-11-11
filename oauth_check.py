"""Validate refresh-token access without ever printing OAuth secrets."""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def main() -> int:
    required = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        print("ERROR: Missing required OAuth environment variables: " + ", ".join(missing), file=sys.stderr)
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
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channel = yt.channels().list(part="id", mine=True, maxResults=1).execute()
        if not channel.get("items"):
            raise RuntimeError("OAuth succeeded but no YouTube channel was returned.")

        analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        yesterday = date.today() - timedelta(days=1)
        analytics.reports().query(
            ids="channel==MINE",
            startDate=(yesterday - timedelta(days=27)).isoformat(),
            endDate=yesterday.isoformat(),
            metrics="views",
        ).execute()

        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        try:
            os.chmod("token.json", 0o600)
        except OSError:
            pass
    except HttpError as exc:
        print(f"ERROR: Google API permission check failed (HTTP {exc.resp.status}).", file=sys.stderr)
        print("The refresh token must belong to the configured OAuth client and include upload, YouTube read, and YouTube Analytics read scopes.", file=sys.stderr)
        return 1
    except Exception as exc:
        # Exception messages from OAuth may contain request details; do not print them.
        print(f"ERROR: YouTube OAuth validation failed ({type(exc).__name__}).", file=sys.stderr)
        print("Check that Client ID, Client Secret, and Refresh Token come from the same OAuth client and that the refresh token was granted all three required scopes.", file=sys.stderr)
        return 1

    print("OK: OAuth refresh, channel read, and YouTube Analytics read access verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
