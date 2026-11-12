"""Validate refresh-token access and report safe Google OAuth diagnostics."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, timedelta
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def safe_oauth_details(exc: RefreshError) -> tuple[str, str]:
    """Extract only Google's error code/description; never print request or token data."""
    data: Any = getattr(exc, "response_data", None)
    if not isinstance(data, dict):
        for arg in getattr(exc, "args", ()):
            if isinstance(arg, dict):
                data = arg
                break
            if isinstance(arg, str):
                try:
                    parsed = json.loads(arg)
                    if isinstance(parsed, dict):
                        data = parsed
                        break
                except (TypeError, ValueError):
                    continue

    code = data.get("error", "") if isinstance(data, dict) else ""
    description = data.get("error_description", "") if isinstance(data, dict) else ""
    if not code:
        message = str(exc).lower()
        code = next(
            (item for item in ("unauthorized_client", "invalid_grant", "invalid_client", "invalid_scope") if item in message),
            "unknown_oauth_error",
        )

    # Redact all configured credentials defensively, and keep diagnostics bounded.
    for name in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        secret = os.getenv(name, "").strip()
        if secret:
            description = description.replace(secret, "[REDACTED]")
    description = re.sub(r"(?i)(access_token|refresh_token|client_secret)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", str(description))
    description = re.sub(r"\s+", " ", description).strip()[:300]
    return str(code)[:80], description


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
    phase = "OAuth refresh"
    try:
        creds.refresh(Request())
        phase = "YouTube Data API channel read"
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channel = yt.channels().list(part="id", mine=True, maxResults=1).execute()
        if not channel.get("items"):
            raise RuntimeError("OAuth succeeded but no YouTube channel was returned.")

        phase = "YouTube Analytics API read"
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
    except RefreshError as exc:
        code, description = safe_oauth_details(exc)
        print(f"ERROR: Google OAuth token refresh failed ({code}).", file=sys.stderr)
        if description:
            print(f"Google detail: {description}", file=sys.stderr)
        print(
            "Check that the refresh token was issued to this exact OAuth client, "
            "that the client is enabled, and that the token was generated with all three required scopes.",
            file=sys.stderr,
        )
        return 1
    except HttpError as exc:
        detail = ""
        try:
            payload = json.loads(exc.content.decode("utf-8", errors="replace"))
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            if isinstance(error, dict):
                reasons = error.get("errors", [])
                reason = reasons[0].get("reason", "") if reasons and isinstance(reasons[0], dict) else ""
                message = str(error.get("message", ""))
                detail = "; ".join(part for part in (str(reason), message) if part)
        except (ValueError, TypeError, AttributeError):
            pass
        for name in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
            secret = os.getenv(name, "").strip()
            if secret:
                detail = detail.replace(secret, "[REDACTED]")
        detail = re.sub(r"\\s+", " ", detail).strip()[:300]
        print(f"ERROR: {phase} failed (HTTP {exc.resp.status}).", file=sys.stderr)
        if detail:
            print(f"Google detail: {detail}", file=sys.stderr)
        print("OAuth refresh worked. Check the named API is enabled in the same Google Cloud project and the refresh token has the required scope.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: YouTube OAuth validation failed ({type(exc).__name__}).", file=sys.stderr)
        print("No credential values or request headers were printed.", file=sys.stderr)
        return 1

    print("OK: OAuth refresh, channel read, and YouTube Analytics read access verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
