"""Discover a Gemini model enabled for this API key, without exposing the key."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
PREFERRED = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
)


def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("ERROR: GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 2

    request = urllib.request.Request(
        f"{API_ROOT}/models?pageSize=1000",
        headers={"x-goog-api-key": key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("error", {}).get("message", "")
        except Exception:
            detail = ""
        if exc.code in (401, 403):
            reason = "Google rejected the Gemini API key or it lacks Generative Language API access."
        elif exc.code == 429:
            reason = "Gemini model-list request hit a quota/rate limit."
        else:
            reason = f"Gemini model discovery failed with HTTP {exc.code}."
        print(f"ERROR: {reason} {detail[:300]}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Could not reach Gemini model discovery: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    models = {}
    for item in data.get("models", []):
        name = item.get("name", "").removeprefix("models/")
        methods = item.get("supportedGenerationMethods", [])
        if name and "generateContent" in methods:
            models[name] = item

    selected = next((name for name in PREFERRED if name in models), None)
    if not selected:
        available = ", ".join(sorted(models)[:30]) or "none"
        print(
            "ERROR: This API key has no supported Gemini Flash generation model enabled. "
            f"Models visible to the key: {available}",
            file=sys.stderr,
        )
        return 1

    # Persist the actual key-authorized model for later steps in this GitHub job.
    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as env_file:
            env_file.write(f"LLM_MODEL={selected}\n")
    print(f"OK: API key can access {len(models)} content-generation models; selected {selected}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
